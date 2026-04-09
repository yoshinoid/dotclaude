"""Process session parser, ported from TypeScript parsers/process-sessions.ts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dotclaude_types.models import ProcessStats

from dotclaude.parser.utils import safe_json_parse


def _is_record(value: Any) -> bool:
    return isinstance(value, dict)


def parse_process_sessions(session_files: list[str]) -> ProcessStats:
    """Read all sessions/*.json files and aggregate process metadata."""
    by_kind: dict[str, int] = {}
    by_entrypoint: dict[str, int] = {}

    for file_path in session_files:
        try:
            raw = Path(file_path).read_text(encoding="utf-8")
        except OSError:
            continue

        parsed = safe_json_parse(raw)
        if not _is_record(parsed):
            continue

        assert isinstance(parsed, dict)

        kind = parsed.get("kind")
        if isinstance(kind, str) and kind:
            by_kind[kind] = by_kind.get(kind, 0) + 1

        entrypoint = parsed.get("entrypoint")
        if isinstance(entrypoint, str) and entrypoint:
            by_entrypoint[entrypoint] = by_entrypoint.get(entrypoint, 0) + 1

    return ProcessStats(by_kind=by_kind, by_entrypoint=by_entrypoint)
