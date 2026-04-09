"""Parser package — analyze ~/.claude directory and return DotClaudeData.

Public API:
    analyze(options) -> DotClaudeData
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timezone
from pathlib import Path

from dotclaude import __version__ as PACKAGE_VERSION
from dotclaude_types.models import (
    AnalyzeOptions,
    CacheStats,
    CostByDay,
    CostByModel,
    CostEstimate,
    DailyActivity,
    DotClaudeData,
    DotClaudeMeta,
    DotClaudeMetaFilters,
    FileActivity,
    HookFrequency,
    HookFrequencyStats,
    ModelTokenUsage,
    PluginsStatus,
    ProjectStats,
    SessionDurationStats,
    SummaryStats,
    TopDirectory,
)
from dotclaude.parser.parsers.configs import ConfigsParseInput, parse_configs
from dotclaude.parser.parsers.conversations import parse_conversations
from dotclaude.parser.parsers.plugins import parse_plugins
from dotclaude.parser.parsers.process_sessions import parse_process_sessions
from dotclaude.parser.parsers.projects import parse_projects
from dotclaude.parser.parsers.settings import RawHookDefinition
from dotclaude.parser.parsers.subagents import parse_subagents
from dotclaude.parser.scanner import scan_claude_dir
from dotclaude.parser.utils import get_claude_dir, normalize_cwd

__all__ = [
    "analyze",
    "scan_claude_dir",
    "get_claude_dir",
    "normalize_cwd",
    "PACKAGE_VERSION",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_token_usage(
    accumulators: dict[
        str,
        object,  # ModelAccumulator
    ],
) -> list[ModelTokenUsage]:
    """Build ModelTokenUsage list from model accumulators map."""
    from dotclaude.parser.parsers.conversations import ModelAccumulator

    result: list[ModelTokenUsage] = []
    for model, acc in accumulators.items():
        assert isinstance(acc, ModelAccumulator)
        result.append(
            ModelTokenUsage(
                model=model,
                input_tokens=acc.input_tokens,
                output_tokens=acc.output_tokens,
                cache_creation_tokens=acc.cache_creation_tokens,
                cache_read_tokens=acc.cache_read_tokens,
            )
        )
    result.sort(key=lambda x: x.input_tokens, reverse=True)
    return result


def _build_cost_estimate(
    accumulators: dict[str, object],
    daily_cost: dict[str, float],
) -> CostEstimate:
    """Build CostEstimate from model accumulators and daily cost map."""
    from dotclaude.parser.parsers.conversations import ModelAccumulator

    by_model: list[CostByModel] = []
    for model, acc in accumulators.items():
        assert isinstance(acc, ModelAccumulator)
        by_model.append(CostByModel(model=model, cost=acc.cost))
    by_model.sort(key=lambda x: x.cost, reverse=True)

    total = sum(m.cost for m in by_model)

    by_day: list[CostByDay] = sorted(
        [CostByDay(date=date, cost=cost) for date, cost in daily_cost.items()],
        key=lambda x: x.date,
    )

    return CostEstimate(total=total, by_model=by_model, by_day=by_day)


def _build_daily_activity(
    activity_map: dict[str, object],
) -> list[DailyActivity]:
    """Merge daily activity from conversations parser into DailyActivity list."""
    from dotclaude.parser.parsers.conversations import DailyEntry

    result: list[DailyActivity] = []
    for date, entry in activity_map.items():
        assert isinstance(entry, DailyEntry)
        result.append(DailyActivity(date=date, prompts=entry.prompts, sessions=len(entry.sessions)))
    result.sort(key=lambda x: x.date)
    return result


def _build_summary_stats(
    *,
    total_sessions: int,
    total_prompts: int,
    total_assistant_messages: int,
    daily_activity: list[DailyActivity],
    first_activity: str | None,
    last_activity: str | None,
) -> SummaryStats:
    """Build SummaryStats from conversations parse result and other data."""
    days_active = sum(1 for d in daily_activity if d.prompts > 0 or d.sessions > 0)
    epoch_iso = datetime.fromtimestamp(0, tz=UTC).isoformat()

    return SummaryStats(
        total_sessions=total_sessions,
        total_prompts=total_prompts,
        total_assistant_messages=total_assistant_messages,
        days_active=days_active,
        first_activity=first_activity if first_activity is not None else epoch_iso,
        last_activity=last_activity if last_activity is not None else epoch_iso,
    )


def _build_session_durations(
    session_timestamps: dict[str, object],
) -> SessionDurationStats:
    """Build SessionDurationStats from session timestamp ranges."""
    from dotclaude.parser.parsers.conversations import SessionTimestamps

    count = 0
    total_seconds = 0.0
    max_seconds = 0.0

    for _, ts in session_timestamps.items():
        assert isinstance(ts, SessionTimestamps)
        try:
            start_dt = datetime.fromisoformat(ts.first.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(ts.last.replace("Z", "+00:00"))
        except ValueError:
            continue
        if end_dt <= start_dt:
            continue

        duration_sec = (end_dt - start_dt).total_seconds()
        count += 1
        total_seconds += duration_sec
        if duration_sec > max_seconds:
            max_seconds = duration_sec

    return SessionDurationStats(
        count=count,
        total_seconds=round(total_seconds),
        average_seconds=round(total_seconds / count) if count > 0 else 0,
        max_seconds=round(max_seconds),
    )


def _build_cache_stats(token_usage: list[ModelTokenUsage]) -> CacheStats:
    """Build CacheStats from token usage data."""
    cache_read_tokens = 0
    cache_creation_tokens = 0
    total_input_tokens = 0

    for usage in token_usage:
        cache_read_tokens += usage.cache_read_tokens
        cache_creation_tokens += usage.cache_creation_tokens
        total_input_tokens += usage.input_tokens

    denominator = cache_read_tokens + total_input_tokens
    hit_rate = cache_read_tokens / denominator if denominator > 0 else 0.0

    return CacheStats(
        cache_read_tokens=cache_read_tokens,
        cache_creation_tokens=cache_creation_tokens,
        total_input_tokens=total_input_tokens,
        hit_rate=hit_rate,
    )


def _extract_hook_name(command: str) -> str:
    """Extract a short display name from a hook command string.

    e.g., 'bash "C:/Users/jeong/.claude/hooks/pre-bash-security.sh"' -> "pre-bash-security.sh"
    """
    match = re.search(r"[/\\]([^/\\]+?)[\"']?\s*$", command)
    if match:
        return match.group(1)
    # Fallback: last 40 chars
    return "..." + command[-37:] if len(command) > 40 else command


def _build_hook_frequency(
    hook_definitions: list[RawHookDefinition],
    tool_usage: dict[str, int],
    total_sessions: int,
) -> HookFrequencyStats:
    """Build HookFrequencyStats by cross-referencing hook definitions with tool usage.

    Estimation rules:
    - PreToolUse/PostToolUse: sum tool usage for tools matching the matcher pattern
    - SessionStart: fires once per session
    - Stop: fires once per session
    - Other events with empty matcher: fires once per session (conservative estimate)
    """
    hooks: list[HookFrequency] = []

    for defn in hook_definitions:
        estimated_runs = 0

        if defn.event in ("SessionStart", "Stop"):
            estimated_runs = total_sessions
        elif defn.event in ("PreToolUse", "PostToolUse"):
            if len(defn.matcher) == 0:
                # Empty matcher = matches all tool uses
                estimated_runs = sum(tool_usage.values())
            else:
                # Matcher is pipe-separated tool names
                matcher_tools = [s.strip() for s in defn.matcher.split("|")]
                for tool in matcher_tools:
                    estimated_runs += tool_usage.get(tool, 0)
        elif defn.event == "Notification":
            estimated_runs = 0
        else:
            estimated_runs = total_sessions

        command_short = _extract_hook_name(defn.command)
        hooks.append(
            HookFrequency(
                event=defn.event,
                matcher=defn.matcher,
                command=command_short,
                estimated_runs=estimated_runs,
            )
        )

    hooks.sort(key=lambda h: h.estimated_runs, reverse=True)
    total_estimated_runs = sum(h.estimated_runs for h in hooks)

    return HookFrequencyStats(total_estimated_runs=total_estimated_runs, hooks=hooks)


def _build_file_activity(
    extension_counts: dict[str, int],
    directory_counts: dict[str, int],
) -> FileActivity | None:
    """Build FileActivity from extension and directory count maps.

    Returns None if no file activity was recorded.
    """
    if not extension_counts:
        return None

    top_directories: list[TopDirectory] = sorted(
        [TopDirectory(path=p, count=c) for p, c in directory_counts.items()],
        key=lambda x: x.count,
        reverse=True,
    )[:10]

    return FileActivity(by_extension=dict(extension_counts), top_directories=top_directories)


def _assign_cwd_breakdowns(
    projects: list[ProjectStats],
    cwd_accumulators: dict[str, object],
) -> None:
    """Match cwd accumulators from conversations to project stats and populate breakdowns.

    Uses exact match first, then longest-prefix match for subdirectory cwds.
    """
    from dotclaude_types.models import ProjectBreakdown
    from dotclaude.parser.parsers.conversations import CwdAccumulator

    if not cwd_accumulators:
        return

    normalized_paths = [normalize_cwd(p.decoded_path) for p in projects]

    for cwd, acc in cwd_accumulators.items():
        assert isinstance(acc, CwdAccumulator)

        # Exact match first
        match_idx = -1
        try:
            match_idx = normalized_paths.index(cwd)
        except ValueError:
            pass

        # Longest prefix match
        if match_idx == -1:
            longest_len = 0
            for i, pp in enumerate(normalized_paths):
                if pp and cwd.startswith(pp + "/") and len(pp) > longest_len:
                    longest_len = len(pp)
                    match_idx = i

        if match_idx == -1:
            continue

        project = projects[match_idx]

        if project.breakdown is None:
            project.breakdown = ProjectBreakdown(
                tool_usage=dict(acc.tool_usage),
                file_extensions=dict(acc.file_extensions),
                agent_usage=dict(acc.agent_usage),
                model_usage=dict(acc.model_usage),
            )
        else:
            for k, v in acc.tool_usage.items():
                project.breakdown.tool_usage[k] = project.breakdown.tool_usage.get(k, 0) + v
            for k, v in acc.file_extensions.items():
                project.breakdown.file_extensions[k] = (
                    project.breakdown.file_extensions.get(k, 0) + v
                )
            for k, v in acc.agent_usage.items():
                project.breakdown.agent_usage[k] = project.breakdown.agent_usage.get(k, 0) + v
            for k, v in acc.model_usage.items():
                project.breakdown.model_usage[k] = project.breakdown.model_usage.get(k, 0) + v

        project.prompt_count += acc.prompt_count


# ---------------------------------------------------------------------------
# Main analyze function
# ---------------------------------------------------------------------------


async def analyze(options_or_dir: str | AnalyzeOptions | dict[str, object] | None = None) -> DotClaudeData:
    """Analyze the ~/.claude directory and return comprehensive usage analytics.

    This function never crashes on malformed data — all parsers are defensive.

    Args:
        options_or_dir: Either an AnalyzeOptions object, a string path (backward compat),
                        or None to use the default ~/.claude directory.

    Returns:
        DotClaudeData with all parsed and aggregated usage statistics.
    """
    if isinstance(options_or_dir, str):
        opts = AnalyzeOptions(claude_dir=options_or_dir)
    elif options_or_dir is None:
        opts = AnalyzeOptions()
    elif isinstance(options_or_dir, dict):
        opts = AnalyzeOptions.model_validate(options_or_dir)
    else:
        opts = options_or_dir

    resolved_dir = opts.claude_dir if opts.claude_dir is not None else str(get_claude_dir())

    # 1. Discover files
    manifest = scan_claude_dir(resolved_dir)

    # 2. Parse conversations (core — streaming)
    from dotclaude.parser.parsers.conversations import ConversationsFilterOptions

    conversations = parse_conversations(
        manifest.project_dirs,
        filters=ConversationsFilterOptions(since=opts.since, until=opts.until),
    )

    # 3. Parse process sessions
    process_stats = parse_process_sessions(manifest.session_files)

    # 4. Parse subagents
    subagent_stats = parse_subagents(manifest.project_dirs)

    # 5. Parse configs
    config_input = ConfigsParseInput(
        agent_files=manifest.agent_files,
        command_files=manifest.command_files,
        hook_dir=manifest.hook_dir,
        rule_dirs=manifest.rule_dirs,
        skill_dirs=manifest.skill_dirs,
        settings_file=manifest.settings_file,
    )
    config_partial = parse_configs(config_input)

    # 6. Parse plugins
    plugins_status: PluginsStatus = PluginsStatus(
        marketplace_count=0, marketplaces=[], blocked_count=0
    )
    if manifest.plugins_dir is not None:
        plugins_status = parse_plugins(manifest.plugins_dir)

    # 7. Parse projects
    projects = parse_projects(manifest.project_dirs)

    # 8. Assign per-project breakdowns from conversation cwd data
    _assign_cwd_breakdowns(projects, conversations.cwd_accumulators)

    # 9. Build output structures
    token_usage = _build_token_usage(conversations.model_accumulators)
    cost_estimate = _build_cost_estimate(conversations.model_accumulators, conversations.daily_cost)
    daily_activity = _build_daily_activity(conversations.daily_activity)

    total_sessions = len(conversations.session_ids)
    summary_stats = _build_summary_stats(
        total_sessions=total_sessions,
        total_prompts=conversations.total_prompts,
        total_assistant_messages=conversations.total_assistant_messages,
        daily_activity=daily_activity,
        first_activity=conversations.first_activity,
        last_activity=conversations.last_activity,
    )

    tool_usage = dict(conversations.tool_usage)

    from dotclaude_types.models import ConfigStatus

    config_status = ConfigStatus(
        agents=config_partial.agents,
        commands=config_partial.commands,
        hooks=config_partial.hooks,
        rules=config_partial.rules,
        skills=config_partial.skills,
        plugins=plugins_status,
        mcp_servers=config_partial.mcp_servers,
    )

    # 10. Build session duration stats
    session_durations = _build_session_durations(conversations.session_timestamps)

    # 11. Build cache stats
    cache_stats = _build_cache_stats(token_usage)

    # 12. Build hook execution frequency estimates
    hook_frequency = _build_hook_frequency(
        config_partial.hook_definitions,
        tool_usage,
        total_sessions,
    )

    # 13. Build file activity
    file_activity = _build_file_activity(
        conversations.extension_counts,
        conversations.directory_counts,
    )

    # Build filters meta
    filters: DotClaudeMetaFilters | None = None
    if opts.since is not None or opts.until is not None:
        filters = DotClaudeMetaFilters(since=opts.since, until=opts.until)

    return DotClaudeData(
        meta=DotClaudeMeta(
            claude_dir=resolved_dir,
            scanned_at=datetime.now(tz=UTC).isoformat(),
            version=PACKAGE_VERSION,
            filters=filters,
        ),
        summary=summary_stats,
        tool_usage=tool_usage,
        token_usage=token_usage,
        cost_estimate=cost_estimate,
        projects=projects,
        daily_activity=daily_activity,
        process_stats=process_stats,
        subagent_stats=subagent_stats,
        config_status=config_status,
        session_durations=session_durations,
        cache_stats=cache_stats,
        hook_frequency=hook_frequency,
        file_activity=file_activity,
    )
