"""Conversations parser, ported from TypeScript parsers/conversations.ts.

This is the core parser: streams JSONL files, accumulates token/cost data,
extracts tool usage, file activity, and per-cwd breakdowns in a single pass.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotclaude.parser.pricing import UsageForCost, calculate_cost
from dotclaude.parser.utils import normalize_cwd, stream_jsonl

# ---------------------------------------------------------------------------
# Internal accumulators
# ---------------------------------------------------------------------------


@dataclass
class ModelAccumulator:
    """Token and cost accumulator per model."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    cost: float = 0.0


@dataclass
class CwdAccumulator:
    """Per working-directory accumulator for project breakdown."""

    tool_usage: dict[str, int] = field(default_factory=dict)
    file_extensions: dict[str, int] = field(default_factory=dict)
    agent_usage: dict[str, int] = field(default_factory=dict)
    model_usage: dict[str, int] = field(default_factory=dict)
    prompt_count: int = 0


@dataclass
class DailyEntry:
    """Daily activity entry."""

    prompts: int = 0
    sessions: set[str] = field(default_factory=set)


@dataclass
class SessionTimestamps:
    """First and last ISO timestamps for a session."""

    first: str
    last: str


@dataclass
class ConversationsParseResult:
    """Aggregated result from streaming all conversation JSONL files."""

    # model → aggregated token counts
    model_accumulators: dict[str, ModelAccumulator] = field(default_factory=dict)
    # tool name → call count
    tool_usage: dict[str, int] = field(default_factory=dict)
    # date (YYYY-MM-DD) → DailyEntry
    daily_activity: dict[str, DailyEntry] = field(default_factory=dict)
    # all unique session IDs seen
    session_ids: set[str] = field(default_factory=set)
    total_prompts: int = 0
    total_assistant_messages: int = 0
    first_activity: str | None = None
    last_activity: str | None = None
    # date → total cost
    daily_cost: dict[str, float] = field(default_factory=dict)
    # sessionId → SessionTimestamps
    session_timestamps: dict[str, SessionTimestamps] = field(default_factory=dict)
    # file extension → count from tool_use file paths
    extension_counts: dict[str, int] = field(default_factory=dict)
    # directory path → count from tool_use file paths
    directory_counts: dict[str, int] = field(default_factory=dict)
    # normalized cwd → per-project accumulator
    cwd_accumulators: dict[str, CwdAccumulator] = field(default_factory=dict)


@dataclass
class ConversationsFilterOptions:
    """Date range filters for conversation parsing."""

    since: str | None = None
    until: str | None = None


# ---------------------------------------------------------------------------
# Type guards
# ---------------------------------------------------------------------------


def _is_record(value: Any) -> bool:
    return isinstance(value, dict)


def _is_assistant_record(value: Any) -> bool:
    return (
        _is_record(value)
        and value.get("type") == "assistant"
        and _is_record(value.get("message"))
        and isinstance(value["message"].get("model"), str)
    )


def _is_user_record(value: Any) -> bool:
    return (
        _is_record(value)
        and value.get("type") == "user"
        and _is_record(value.get("message"))
        and value["message"].get("role") == "user"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Tools known to have a `file_path` string in their input.
_FILE_PATH_TOOLS: frozenset[str] = frozenset(["Write", "Edit", "Read", "MultiEdit"])


def _timestamp_to_date(ts: str) -> str:
    """Convert an ISO timestamp string to a YYYY-MM-DD date string."""
    try:
        return ts[:10] if len(ts) >= 10 else ""
    except (TypeError, AttributeError):
        return ""


def _update_activity_timestamps(result: ConversationsParseResult, date: str) -> None:
    if not date:
        return
    if result.first_activity is None or date < result.first_activity:
        result.first_activity = date
    if result.last_activity is None or date > result.last_activity:
        result.last_activity = date


def _update_session_timestamps(
    result: ConversationsParseResult, session_id: str, timestamp: str
) -> None:
    if not session_id or not timestamp:
        return
    existing = result.session_timestamps.get(session_id)
    if existing is None:
        result.session_timestamps[session_id] = SessionTimestamps(
            first=timestamp, last=timestamp
        )
    else:
        if timestamp < existing.first:
            existing.first = timestamp
        if timestamp > existing.last:
            existing.last = timestamp


def _extract_relative_dir(file_path: str) -> str:
    """Extract a short relative directory from an absolute file path.

    Strips drive letters and leading slashes, then takes up to the last 3 segments
    before the filename.

    Example: ``C:\\Users\\foo\\projects\\bar\\src\\index.ts`` → ``projects/bar/src``
    """
    import re

    normalized = file_path.replace("\\", "/")
    # Remove drive letter (C:) or leading /c/ (Git Bash style)
    stripped = re.sub(r"^[A-Za-z]:/", "", normalized)
    stripped = re.sub(r"^/[A-Za-z]/", "", stripped)
    segments = [s for s in stripped.split("/") if s]
    # Need at least a directory + filename
    if len(segments) < 2:
        return ""
    # Take last 3 directory segments (excluding filename)
    dir_segments = segments[:-1]
    meaningful = dir_segments[-3:]
    return "/".join(meaningful)


def _get_or_create_daily_entry(result: ConversationsParseResult, date: str) -> DailyEntry:
    entry = result.daily_activity.get(date)
    if entry is None:
        entry = DailyEntry()
        result.daily_activity[date] = entry
    return entry


def _get_or_create_cwd_accumulator(
    result: ConversationsParseResult, cwd: str
) -> CwdAccumulator:
    acc = result.cwd_accumulators.get(cwd)
    if acc is None:
        acc = CwdAccumulator()
        result.cwd_accumulators[cwd] = acc
    return acc


# ---------------------------------------------------------------------------
# Per-record handlers
# ---------------------------------------------------------------------------


def _handle_assistant(record: dict[str, Any], result: ConversationsParseResult) -> None:
    result.total_assistant_messages += 1

    message = record["message"]
    model: str = message.get("model", "")
    usage = message.get("usage", {})
    content = message.get("content", [])
    session_id: str = record.get("sessionId", "")
    timestamp: str = record.get("timestamp", "")

    date = _timestamp_to_date(timestamp)
    _update_activity_timestamps(result, date)

    if session_id:
        result.session_ids.add(session_id)
        _update_session_timestamps(result, session_id, timestamp)

    # Token aggregation
    acc = result.model_accumulators.get(model)
    if acc is None:
        acc = ModelAccumulator()
        result.model_accumulators[model] = acc

    acc.input_tokens += usage.get("input_tokens", 0) or 0
    acc.output_tokens += usage.get("output_tokens", 0) or 0
    acc.cache_creation_tokens += usage.get("cache_creation_input_tokens", 0) or 0
    acc.cache_read_tokens += usage.get("cache_read_input_tokens", 0) or 0

    cost = calculate_cost(
        model,
        UsageForCost(
            input_tokens=usage.get("input_tokens", 0) or 0,
            output_tokens=usage.get("output_tokens", 0) or 0,
            cache_creation_input_tokens=usage.get("cache_creation_input_tokens", 0) or 0,
            cache_read_input_tokens=usage.get("cache_read_input_tokens", 0) or 0,
        ),
    )
    acc.cost += cost

    if date:
        result.daily_cost[date] = result.daily_cost.get(date, 0.0) + cost

    # Per-cwd accumulator (if cwd is present)
    cwd: str | None = record.get("cwd")
    cwd_acc: CwdAccumulator | None = None
    if isinstance(cwd, str) and cwd:
        normalized = normalize_cwd(cwd)
        cwd_acc = _get_or_create_cwd_accumulator(result, normalized)
        cwd_acc.model_usage[model] = cwd_acc.model_usage.get(model, 0) + 1

    # Tool usage + file path extraction + per-cwd accumulation (single pass)
    if isinstance(content, list):
        for block in content:
            if not _is_record(block):
                continue
            if block.get("type") != "tool_use":
                continue
            tool_name = block.get("name")
            if not isinstance(tool_name, str):
                continue

            result.tool_usage[tool_name] = result.tool_usage.get(tool_name, 0) + 1
            if cwd_acc is not None:
                cwd_acc.tool_usage[tool_name] = cwd_acc.tool_usage.get(tool_name, 0) + 1

            # Extract agent subagent_type for per-cwd tracking
            block_input = block.get("input")
            if tool_name == "Agent" and cwd_acc is not None and _is_record(block_input):
                agent_type = block_input.get("subagent_type")  # type: ignore[union-attr]
                if isinstance(agent_type, str) and agent_type:
                    cwd_acc.agent_usage[agent_type] = (
                        cwd_acc.agent_usage.get(agent_type, 0) + 1
                    )

            # Extract file_path from tools that operate on files
            if tool_name in _FILE_PATH_TOOLS and _is_record(block_input):
                file_path = block_input.get("file_path")  # type: ignore[union-attr]
                if isinstance(file_path, str) and file_path:
                    p = Path(file_path)
                    ext = p.suffix.lower()
                    key = ext if ext else p.name
                    if key:
                        result.extension_counts[key] = (
                            result.extension_counts.get(key, 0) + 1
                        )
                        if cwd_acc is not None:
                            cwd_acc.file_extensions[key] = (
                                cwd_acc.file_extensions.get(key, 0) + 1
                            )
                    dir_path = _extract_relative_dir(file_path)
                    if dir_path:
                        result.directory_counts[dir_path] = (
                            result.directory_counts.get(dir_path, 0) + 1
                        )


def _handle_user(record: dict[str, Any], result: ConversationsParseResult) -> None:
    result.total_prompts += 1

    session_id: str = record.get("sessionId", "")
    timestamp: str = record.get("timestamp", "")
    date = _timestamp_to_date(timestamp)
    _update_activity_timestamps(result, date)

    if session_id:
        result.session_ids.add(session_id)
        _update_session_timestamps(result, session_id, timestamp)
        if date:
            entry = _get_or_create_daily_entry(result, date)
            entry.sessions.add(session_id)

    if date:
        entry = _get_or_create_daily_entry(result, date)
        entry.prompts += 1

    # Per-cwd prompt count
    cwd: str | None = record.get("cwd")
    if isinstance(cwd, str) and cwd:
        normalized = normalize_cwd(cwd)
        cwd_acc = _get_or_create_cwd_accumulator(result, normalized)
        cwd_acc.prompt_count += 1


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

_IGNORE_NAMES: frozenset[str] = frozenset(
    [
        "cache",
        "backups",
        "file-history",
        "ide",
        "shell-snapshots",
        "session-env",
    ]
)


def _collect_jsonl_files(directory: Path) -> list[Path]:
    """Collect all .jsonl files within a project directory tree.

    Skips subdirectories whose names are in the ignore list.
    """
    results: list[Path] = []
    try:
        entries = list(directory.iterdir())
    except OSError:
        return results

    for entry in entries:
        if entry.name in _IGNORE_NAMES:
            continue
        if entry.is_dir():
            results.extend(_collect_jsonl_files(entry))
        elif entry.is_file() and entry.suffix == ".jsonl":
            results.append(entry)

    return results


def parse_conversations(
    project_dirs: list[str],
    filters: ConversationsFilterOptions | None = None,
) -> ConversationsParseResult:
    """Stream all conversation JSONL files across all project directories.

    Only extracts metadata — message text content is never stored.
    """
    result = ConversationsParseResult()

    for project_dir in project_dirs:
        jsonl_files = _collect_jsonl_files(Path(project_dir))

        for file_path in jsonl_files:
            try:
                records = stream_jsonl(file_path)
            except OSError:
                continue

            for record in records:
                # Apply date filters if provided
                if filters is not None and (filters.since is not None or filters.until is not None):
                    ts: str | None = None
                    if _is_assistant_record(record):
                        ts = record.get("timestamp")
                    elif _is_user_record(record):
                        ts = record.get("timestamp")

                    if ts is not None:
                        date = _timestamp_to_date(ts)
                        if date:
                            if filters.since is not None and date < filters.since:
                                continue
                            if filters.until is not None and date > filters.until:
                                continue

                if _is_assistant_record(record):
                    _handle_assistant(record, result)
                elif _is_user_record(record):
                    _handle_user(record, result)
                # All other record types are skipped

    return result
