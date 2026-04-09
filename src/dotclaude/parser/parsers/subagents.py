"""Subagent parser, ported from TypeScript parsers/subagents.ts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dotclaude.models import SubagentStats
from dotclaude.parser.utils import safe_json_parse


def _is_record(value: Any) -> bool:
    return isinstance(value, dict)


def _collect_meta_files(directory: Path) -> list[Path]:
    """Recursively find all ``agent-*.meta.json`` files under a directory."""
    results: list[Path] = []
    try:
        entries = list(directory.iterdir())
    except OSError:
        return results

    for entry in entries:
        if entry.is_dir():
            results.extend(_collect_meta_files(entry))
        elif (
            entry.is_file()
            and entry.name.startswith("agent-")
            and entry.name.endswith(".meta.json")
        ):
            results.append(entry)

    return results


def parse_subagents(project_dirs: list[str]) -> SubagentStats:
    """Scan all project directories for subagent .meta.json files and aggregate
    subagent run statistics by type.
    """
    by_type: dict[str, int] = {}
    total_runs = 0

    for project_dir in project_dirs:
        meta_files = _collect_meta_files(Path(project_dir))

        for file_path in meta_files:
            try:
                raw = file_path.read_text(encoding="utf-8")
            except OSError:
                continue

            parsed = safe_json_parse(raw)
            if not _is_record(parsed):
                continue

            assert isinstance(parsed, dict)
            total_runs += 1

            agent_type_raw = parsed.get("agentType")
            agent_type = (
                agent_type_raw
                if isinstance(agent_type_raw, str) and agent_type_raw
                else "unknown"
            )
            by_type[agent_type] = by_type.get(agent_type, 0) + 1

    return SubagentStats(total_runs=total_runs, by_type=by_type)
