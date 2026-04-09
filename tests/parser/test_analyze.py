"""Integration tests for the analyze() orchestrator function.

Ported from TypeScript: src/__tests__/parser/analyze.test.ts
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from dotclaude.parser import analyze


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _assistant_record(
    *,
    session_id: str,
    timestamp: str,
    model: str = "claude-sonnet-4-5-20250514",
    input_tokens: int = 100,
    output_tokens: int = 50,
    cache_read: int = 0,
    cache_write: int = 0,
) -> str:
    import random
    import string

    uid = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return json.dumps(
        {
            "type": "assistant",
            "uuid": f"uuid-{uid}",
            "parentUuid": None,
            "isSidechain": False,
            "sessionId": session_id,
            "timestamp": timestamp,
            "message": {
                "id": f"msg-{uid}",
                "type": "message",
                "role": "assistant",
                "model": model,
                "content": [],
                "stop_reason": "end_turn",
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cache_creation_input_tokens": cache_write,
                    "cache_read_input_tokens": cache_read,
                },
            },
        }
    )


def _user_record(*, session_id: str, timestamp: str) -> str:
    import random
    import string

    uid = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return json.dumps(
        {
            "type": "user",
            "uuid": f"uuid-{uid}",
            "parentUuid": None,
            "isSidechain": False,
            "sessionId": session_id,
            "timestamp": timestamp,
            "message": {"role": "user", "content": "test"},
        }
    )


@pytest.fixture
def claude_dir_with_data(tmp_path: Path) -> Path:
    """Create a claude dir with sample conversation data."""
    project_dir = tmp_path / "projects" / "test-project"
    project_dir.mkdir(parents=True)

    lines = [
        _user_record(session_id="s1", timestamp="2025-04-01T10:00:00Z"),
        _assistant_record(
            session_id="s1",
            timestamp="2025-04-01T10:05:00Z",
            input_tokens=200,
            output_tokens=100,
            cache_read=500,
            cache_write=100,
        ),
        _user_record(session_id="s1", timestamp="2025-04-01T10:10:00Z"),
        _assistant_record(
            session_id="s1",
            timestamp="2025-04-01T10:30:00Z",
            input_tokens=300,
            output_tokens=150,
            cache_read=1000,
            cache_write=0,
        ),
        _user_record(session_id="s2", timestamp="2025-04-02T09:00:00Z"),
        _assistant_record(
            session_id="s2",
            timestamp="2025-04-02T09:15:00Z",
            input_tokens=100,
            output_tokens=50,
        ),
    ]

    (project_dir / "convo.jsonl").write_text("\n".join(lines), encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_returns_complete_dot_claude_data_structure(
    claude_dir_with_data: Path,
) -> None:
    data = await analyze({"claude_dir": str(claude_dir_with_data)})

    assert data.meta.claude_dir == str(claude_dir_with_data)
    assert data.meta.version is not None
    assert data.summary.total_prompts == 3
    assert data.summary.total_assistant_messages == 3
    assert data.summary.total_sessions == 2
    assert data.summary.days_active == 2


@pytest.mark.asyncio
async def test_computes_session_duration_stats(claude_dir_with_data: Path) -> None:
    data = await analyze({"claude_dir": str(claude_dir_with_data)})

    assert data.session_durations.count == 2
    # s1: 10:00 to 10:30 = 1800s, s2: 09:00 to 09:15 = 900s
    assert data.session_durations.max_seconds == 1800
    assert data.session_durations.total_seconds == 2700
    assert data.session_durations.average_seconds == 1350


@pytest.mark.asyncio
async def test_computes_cache_stats(claude_dir_with_data: Path) -> None:
    data = await analyze({"claude_dir": str(claude_dir_with_data)})

    assert data.cache_stats.cache_read_tokens == 1500
    assert data.cache_stats.cache_creation_tokens == 100
    assert data.cache_stats.total_input_tokens == 600
    # hitRate = 1500 / (1500 + 600) ≈ 0.714
    assert abs(data.cache_stats.hit_rate - 0.714) < 0.01


@pytest.mark.asyncio
async def test_applies_since_filter(claude_dir_with_data: Path) -> None:
    from dotclaude.models import AnalyzeOptions

    data = await analyze(AnalyzeOptions(claude_dir=str(claude_dir_with_data), since="2025-04-02"))

    assert data.summary.total_prompts == 1
    assert data.summary.total_assistant_messages == 1
    assert data.meta.filters is not None
    assert data.meta.filters.since == "2025-04-02"


@pytest.mark.asyncio
async def test_applies_until_filter(claude_dir_with_data: Path) -> None:
    from dotclaude.models import AnalyzeOptions

    data = await analyze(AnalyzeOptions(claude_dir=str(claude_dir_with_data), until="2025-04-01"))

    assert data.summary.total_prompts == 2
    assert data.summary.total_assistant_messages == 2
    assert data.meta.filters is not None
    assert data.meta.filters.until == "2025-04-01"


@pytest.mark.asyncio
async def test_backward_compat_string_argument(claude_dir_with_data: Path) -> None:
    data = await analyze(str(claude_dir_with_data))

    assert data.summary.total_prompts == 3
    assert data.meta.filters is None


@pytest.mark.asyncio
async def test_handles_empty_claude_directory(tmp_path: Path) -> None:
    data = await analyze(str(tmp_path))

    assert data.summary.total_prompts == 0
    assert data.session_durations.count == 0
    assert data.cache_stats.hit_rate == 0
