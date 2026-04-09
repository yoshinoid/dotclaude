"""History parser, ported from TypeScript parsers/history.ts."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dotclaude.parser.utils import stream_jsonl


def _is_record(value: Any) -> bool:
    return isinstance(value, dict)


def _timestamp_to_date(ts: float) -> str:
    """Convert a millisecond epoch timestamp to a YYYY-MM-DD string."""
    return datetime.fromtimestamp(ts / 1000.0, tz=UTC).strftime("%Y-%m-%d")


def parse_history(history_file: str) -> dict[str, Any]:
    """Stream history.jsonl and build a daily activity timeline.

    Returns a dict with:
      - ``daily_counts``: dict[str, int] — date (YYYY-MM-DD) → number of prompt entries
      - ``session_ids``: set[str] — all unique session IDs encountered
      - ``projects``: set[str] — all unique project paths encountered
    """
    daily_counts: dict[str, int] = {}
    session_ids: set[str] = set()
    projects: set[str] = set()

    path = Path(history_file)
    for record in stream_jsonl(path):
        if not _is_record(record):
            continue

        assert isinstance(record, dict)

        # Track project paths
        project = record.get("project")
        if isinstance(project, str) and project:
            projects.add(project)

        # Track session IDs
        session_id = record.get("sessionId")
        if isinstance(session_id, str) and session_id:
            session_ids.add(session_id)

        # Build daily timeline from timestamp (ms epoch)
        ts = record.get("timestamp")
        if isinstance(ts, (int, float)):
            date = _timestamp_to_date(float(ts))
            daily_counts[date] = daily_counts.get(date, 0) + 1

    return {
        "daily_counts": daily_counts,
        "session_ids": session_ids,
        "projects": projects,
    }
