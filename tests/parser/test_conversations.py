"""Tests for parser.parsers.conversations, ported from TypeScript conversations.test.ts."""

from __future__ import annotations

import json
import random
import string
from pathlib import Path

import pytest

from dotclaude.parser.parsers.conversations import (
    ConversationsFilterOptions,
    parse_conversations,
)

# ---------------------------------------------------------------------------
# Helpers — build realistic JSONL records
# ---------------------------------------------------------------------------


def _rand_id() -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=8))


def assistant_record(
    *,
    session_id: str,
    timestamp: str,
    model: str = "claude-sonnet-4-5-20250514",
    input_tokens: int = 100,
    output_tokens: int = 50,
    cache_read: int = 0,
    cache_write: int = 0,
    tools: list[str] | None = None,
    tool_inputs: list[dict] | None = None,
    cwd: str | None = None,
) -> str:
    tool_use_blocks = [
        {"type": "tool_use", "id": f"tool_{name}", "name": name, "input": {}}
        for name in (tools or [])
    ]
    input_blocks = [
        {
            "type": "tool_use",
            "id": f"tool_{t['name']}_{_rand_id()}",
            "name": t["name"],
            "input": t["input"],
        }
        for t in (tool_inputs or [])
    ]
    content = tool_use_blocks + input_blocks
    record: dict = {
        "type": "assistant",
        "uuid": f"uuid-{_rand_id()}",
        "parentUuid": None,
        "isSidechain": False,
        "sessionId": session_id,
        "timestamp": timestamp,
        "cwd": cwd,
        "message": {
            "id": f"msg-{_rand_id()}",
            "type": "message",
            "role": "assistant",
            "model": model,
            "content": content,
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_creation_input_tokens": cache_write,
                "cache_read_input_tokens": cache_read,
            },
        },
    }
    return json.dumps(record)


def user_record(
    *,
    session_id: str,
    timestamp: str,
    cwd: str | None = None,
) -> str:
    record: dict = {
        "type": "user",
        "uuid": f"uuid-{_rand_id()}",
        "parentUuid": None,
        "isSidechain": False,
        "sessionId": session_id,
        "timestamp": timestamp,
        "cwd": cwd,
        "message": {"role": "user", "content": "test prompt"},
    }
    return json.dumps(record)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def project_dir(tmp_dir: Path) -> Path:
    d = tmp_dir / "test-project"
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_jsonl(project_dir: Path, filename: str, lines: list[str]) -> None:
    (project_dir / filename).write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_counts_prompts_and_assistant_messages(project_dir: Path) -> None:
    write_jsonl(
        project_dir,
        "session.jsonl",
        [
            user_record(session_id="s1", timestamp="2025-04-01T10:00:00Z"),
            assistant_record(session_id="s1", timestamp="2025-04-01T10:00:05Z"),
            user_record(session_id="s1", timestamp="2025-04-01T10:01:00Z"),
            assistant_record(session_id="s1", timestamp="2025-04-01T10:01:05Z"),
        ],
    )

    result = parse_conversations([str(project_dir)])
    assert result.total_prompts == 2
    assert result.total_assistant_messages == 2
    assert len(result.session_ids) == 1


def test_aggregates_token_usage_by_model(project_dir: Path) -> None:
    write_jsonl(
        project_dir,
        "session.jsonl",
        [
            assistant_record(
                session_id="s1",
                timestamp="2025-04-01T10:00:00Z",
                model="claude-sonnet-4-5-20250514",
                input_tokens=200,
                output_tokens=100,
            ),
            assistant_record(
                session_id="s1",
                timestamp="2025-04-01T10:01:00Z",
                model="claude-sonnet-4-5-20250514",
                input_tokens=300,
                output_tokens=150,
            ),
            assistant_record(
                session_id="s1",
                timestamp="2025-04-01T10:02:00Z",
                model="claude-opus-4-5-20250514",
                input_tokens=500,
                output_tokens=200,
            ),
        ],
    )

    result = parse_conversations([str(project_dir)])
    sonnet = result.model_accumulators.get("claude-sonnet-4-5-20250514")
    opus = result.model_accumulators.get("claude-opus-4-5-20250514")

    assert sonnet is not None
    assert sonnet.input_tokens == 500
    assert sonnet.output_tokens == 250

    assert opus is not None
    assert opus.input_tokens == 500
    assert opus.output_tokens == 200


def test_tracks_tool_usage_counts(project_dir: Path) -> None:
    write_jsonl(
        project_dir,
        "session.jsonl",
        [
            assistant_record(
                session_id="s1",
                timestamp="2025-04-01T10:00:00Z",
                tools=["Read", "Edit", "Read"],
            ),
            assistant_record(
                session_id="s1",
                timestamp="2025-04-01T10:01:00Z",
                tools=["Bash"],
            ),
        ],
    )

    result = parse_conversations([str(project_dir)])
    assert result.tool_usage.get("Read") == 2
    assert result.tool_usage.get("Edit") == 1
    assert result.tool_usage.get("Bash") == 1


def test_builds_daily_activity_map(project_dir: Path) -> None:
    write_jsonl(
        project_dir,
        "session.jsonl",
        [
            user_record(session_id="s1", timestamp="2025-04-01T10:00:00Z"),
            user_record(session_id="s1", timestamp="2025-04-01T11:00:00Z"),
            user_record(session_id="s2", timestamp="2025-04-02T09:00:00Z"),
        ],
    )

    result = parse_conversations([str(project_dir)])
    day1 = result.daily_activity.get("2025-04-01")
    day2 = result.daily_activity.get("2025-04-02")

    assert day1 is not None
    assert day1.prompts == 2
    assert len(day1.sessions) == 1

    assert day2 is not None
    assert day2.prompts == 1
    assert len(day2.sessions) == 1


def test_tracks_first_and_last_activity_timestamps(project_dir: Path) -> None:
    write_jsonl(
        project_dir,
        "session.jsonl",
        [
            user_record(session_id="s1", timestamp="2025-03-15T10:00:00Z"),
            assistant_record(session_id="s1", timestamp="2025-04-20T10:00:00Z"),
        ],
    )

    result = parse_conversations([str(project_dir)])
    assert result.first_activity == "2025-03-15"
    assert result.last_activity == "2025-04-20"


def test_tracks_session_timestamps_for_duration(project_dir: Path) -> None:
    write_jsonl(
        project_dir,
        "session.jsonl",
        [
            user_record(session_id="s1", timestamp="2025-04-01T10:00:00Z"),
            assistant_record(session_id="s1", timestamp="2025-04-01T10:00:30Z"),
            user_record(session_id="s1", timestamp="2025-04-01T10:05:00Z"),
            assistant_record(session_id="s1", timestamp="2025-04-01T10:30:00Z"),
        ],
    )

    result = parse_conversations([str(project_dir)])
    ts = result.session_timestamps.get("s1")

    assert ts is not None
    assert ts.first == "2025-04-01T10:00:00Z"
    assert ts.last == "2025-04-01T10:30:00Z"


def test_accumulates_cache_tokens(project_dir: Path) -> None:
    write_jsonl(
        project_dir,
        "session.jsonl",
        [
            assistant_record(
                session_id="s1",
                timestamp="2025-04-01T10:00:00Z",
                cache_read=1000,
                cache_write=500,
            ),
            assistant_record(
                session_id="s1",
                timestamp="2025-04-01T10:01:00Z",
                cache_read=2000,
                cache_write=0,
            ),
        ],
    )

    result = parse_conversations([str(project_dir)])
    acc = result.model_accumulators.get("claude-sonnet-4-5-20250514")
    assert acc is not None
    assert acc.cache_read_tokens == 3000
    assert acc.cache_creation_tokens == 500


# ---------------------------------------------------------------------------
# Date filters
# ---------------------------------------------------------------------------


@pytest.fixture
def project_dir_with_date_range(project_dir: Path) -> Path:
    write_jsonl(
        project_dir,
        "session.jsonl",
        [
            user_record(session_id="s1", timestamp="2025-03-01T10:00:00Z"),
            assistant_record(session_id="s1", timestamp="2025-03-01T10:00:05Z"),
            user_record(session_id="s1", timestamp="2025-04-01T10:00:00Z"),
            assistant_record(session_id="s1", timestamp="2025-04-01T10:00:05Z"),
            user_record(session_id="s2", timestamp="2025-05-01T10:00:00Z"),
            assistant_record(session_id="s2", timestamp="2025-05-01T10:00:05Z"),
        ],
    )
    return project_dir


def test_filter_since(project_dir_with_date_range: Path) -> None:
    result = parse_conversations(
        [str(project_dir_with_date_range)],
        ConversationsFilterOptions(since="2025-04-01"),
    )
    assert result.total_prompts == 2
    assert result.total_assistant_messages == 2


def test_filter_until(project_dir_with_date_range: Path) -> None:
    result = parse_conversations(
        [str(project_dir_with_date_range)],
        ConversationsFilterOptions(until="2025-04-01"),
    )
    assert result.total_prompts == 2
    assert result.total_assistant_messages == 2


def test_filter_since_and_until_combined(project_dir_with_date_range: Path) -> None:
    result = parse_conversations(
        [str(project_dir_with_date_range)],
        ConversationsFilterOptions(since="2025-04-01", until="2025-04-30"),
    )
    assert result.total_prompts == 1
    assert result.total_assistant_messages == 1


def test_filter_returns_empty_when_no_records_match(project_dir_with_date_range: Path) -> None:
    result = parse_conversations(
        [str(project_dir_with_date_range)],
        ConversationsFilterOptions(since="2026-01-01"),
    )
    assert result.total_prompts == 0
    assert result.total_assistant_messages == 0


def test_handles_empty_project_dirs() -> None:
    result = parse_conversations([])
    assert result.total_prompts == 0
    assert result.total_assistant_messages == 0
    assert len(result.session_ids) == 0


def test_skips_malformed_records_without_crashing(project_dir: Path) -> None:
    write_jsonl(
        project_dir,
        "session.jsonl",
        [
            '{"type": "assistant", "message": "not an object"}',
            '{"type": "unknown_type"}',
            user_record(session_id="s1", timestamp="2025-04-01T10:00:00Z"),
        ],
    )

    result = parse_conversations([str(project_dir)])
    assert result.total_prompts == 1
    assert result.total_assistant_messages == 0


# ---------------------------------------------------------------------------
# File activity extraction
# ---------------------------------------------------------------------------


class TestFileActivity:
    def test_extracts_file_extensions_from_write_edit_read(self, project_dir: Path) -> None:
        write_jsonl(
            project_dir,
            "session.jsonl",
            [
                assistant_record(
                    session_id="s1",
                    timestamp="2025-04-01T10:00:00Z",
                    tool_inputs=[
                        {"name": "Write", "input": {"file_path": "/projects/app/src/index.ts", "content": ""}},
                        {"name": "Edit", "input": {"file_path": "/projects/app/src/utils.ts", "old_string": "", "new_string": ""}},
                        {"name": "Read", "input": {"file_path": "/projects/app/src/main.py"}},
                        {"name": "Read", "input": {"file_path": "/projects/app/tests/test_main.py"}},
                    ],
                )
            ],
        )

        result = parse_conversations([str(project_dir)])
        assert result.extension_counts.get(".ts") == 2
        assert result.extension_counts.get(".py") == 2

    def test_ignores_tools_without_file_path(self, project_dir: Path) -> None:
        write_jsonl(
            project_dir,
            "session.jsonl",
            [
                assistant_record(
                    session_id="s1",
                    timestamp="2025-04-01T10:00:00Z",
                    tool_inputs=[
                        {"name": "Bash", "input": {"command": "ls -la"}},
                        {"name": "Glob", "input": {"pattern": "**/*.ts"}},
                        {"name": "Grep", "input": {"pattern": "TODO", "path": "/app"}},
                    ],
                )
            ],
        )

        result = parse_conversations([str(project_dir)])
        assert len(result.extension_counts) == 0

    def test_handles_files_without_extensions(self, project_dir: Path) -> None:
        write_jsonl(
            project_dir,
            "session.jsonl",
            [
                assistant_record(
                    session_id="s1",
                    timestamp="2025-04-01T10:00:00Z",
                    tool_inputs=[
                        {"name": "Read", "input": {"file_path": "/app/Dockerfile"}},
                        {"name": "Read", "input": {"file_path": "/app/Makefile"}},
                        {"name": "Read", "input": {"file_path": "/app/.gitignore"}},
                    ],
                )
            ],
        )

        result = parse_conversations([str(project_dir)])
        assert result.extension_counts.get("Dockerfile") == 1
        assert result.extension_counts.get("Makefile") == 1
        assert result.extension_counts.get(".gitignore") == 1

    def test_counts_directory_paths_from_file_operations(self, project_dir: Path) -> None:
        write_jsonl(
            project_dir,
            "session.jsonl",
            [
                assistant_record(
                    session_id="s1",
                    timestamp="2025-04-01T10:00:00Z",
                    tool_inputs=[
                        {"name": "Write", "input": {"file_path": "/users/dev/projects/app/src/index.ts", "content": ""}},
                        {"name": "Edit", "input": {"file_path": "/users/dev/projects/app/src/utils.ts", "old_string": "", "new_string": ""}},
                        {"name": "Read", "input": {"file_path": "/users/dev/projects/app/tests/main.py"}},
                    ],
                )
            ],
        )

        result = parse_conversations([str(project_dir)])
        assert result.directory_counts.get("projects/app/src") == 2
        assert result.directory_counts.get("projects/app/tests") == 1

    def test_handles_windows_style_paths(self, project_dir: Path) -> None:
        write_jsonl(
            project_dir,
            "session.jsonl",
            [
                assistant_record(
                    session_id="s1",
                    timestamp="2025-04-01T10:00:00Z",
                    tool_inputs=[
                        {
                            "name": "Write",
                            "input": {
                                "file_path": "C:\\Users\\dev\\projects\\app\\src\\index.ts",
                                "content": "",
                            },
                        }
                    ],
                )
            ],
        )

        result = parse_conversations([str(project_dir)])
        assert result.extension_counts.get(".ts") == 1
        assert len(result.directory_counts) > 0

    def test_skips_tool_use_blocks_with_missing_file_path(self, project_dir: Path) -> None:
        write_jsonl(
            project_dir,
            "session.jsonl",
            [
                assistant_record(
                    session_id="s1",
                    timestamp="2025-04-01T10:00:00Z",
                    tool_inputs=[
                        {"name": "Write", "input": {"content": "no file_path field"}},
                        {"name": "Edit", "input": {"file_path": 123, "old_string": "", "new_string": ""}},
                    ],
                )
            ],
        )

        result = parse_conversations([str(project_dir)])
        assert len(result.extension_counts) == 0


# ---------------------------------------------------------------------------
# Per-cwd accumulation
# ---------------------------------------------------------------------------


class TestCwdAccumulation:
    def test_accumulates_tool_usage_and_prompts_per_cwd(self, project_dir: Path) -> None:
        write_jsonl(
            project_dir,
            "session.jsonl",
            [
                user_record(
                    session_id="s1",
                    timestamp="2025-04-01T10:00:00Z",
                    cwd="C:\\Users\\dev\\projectA",
                ),
                assistant_record(
                    session_id="s1",
                    timestamp="2025-04-01T10:00:05Z",
                    cwd="C:\\Users\\dev\\projectA",
                    tools=["Read", "Edit"],
                ),
                user_record(
                    session_id="s1",
                    timestamp="2025-04-01T10:01:00Z",
                    cwd="C:\\Users\\dev\\projectB",
                ),
                assistant_record(
                    session_id="s1",
                    timestamp="2025-04-01T10:01:05Z",
                    cwd="C:\\Users\\dev\\projectB",
                    tools=["Bash"],
                ),
            ],
        )

        result = parse_conversations([str(project_dir)])
        acc_a = result.cwd_accumulators.get("c:/users/dev/projecta")
        acc_b = result.cwd_accumulators.get("c:/users/dev/projectb")

        assert acc_a is not None
        assert acc_a.prompt_count == 1
        assert acc_a.tool_usage.get("Read") == 1
        assert acc_a.tool_usage.get("Edit") == 1

        assert acc_b is not None
        assert acc_b.prompt_count == 1
        assert acc_b.tool_usage.get("Bash") == 1

    def test_extracts_agent_subagent_type(self, project_dir: Path) -> None:
        write_jsonl(
            project_dir,
            "session.jsonl",
            [
                assistant_record(
                    session_id="s1",
                    timestamp="2025-04-01T10:00:00Z",
                    cwd="/home/dev/project",
                    tool_inputs=[
                        {"name": "Agent", "input": {"subagent_type": "python-pro", "prompt": "test"}},
                        {"name": "Agent", "input": {"subagent_type": "python-pro", "prompt": "test2"}},
                        {"name": "Agent", "input": {"subagent_type": "test-engineer", "prompt": "test3"}},
                    ],
                )
            ],
        )

        result = parse_conversations([str(project_dir)])
        acc = result.cwd_accumulators.get("/home/dev/project")

        assert acc is not None
        assert acc.agent_usage.get("python-pro") == 2
        assert acc.agent_usage.get("test-engineer") == 1

    def test_accumulates_model_usage_per_cwd(self, project_dir: Path) -> None:
        write_jsonl(
            project_dir,
            "session.jsonl",
            [
                assistant_record(
                    session_id="s1",
                    timestamp="2025-04-01T10:00:00Z",
                    cwd="/project",
                    model="claude-sonnet-4-5-20250514",
                ),
                assistant_record(
                    session_id="s1",
                    timestamp="2025-04-01T10:01:00Z",
                    cwd="/project",
                    model="claude-opus-4-5-20250514",
                ),
            ],
        )

        result = parse_conversations([str(project_dir)])
        acc = result.cwd_accumulators.get("/project")

        assert acc is not None
        assert acc.model_usage.get("claude-sonnet-4-5-20250514") == 1
        assert acc.model_usage.get("claude-opus-4-5-20250514") == 1

    def test_skips_records_without_cwd(self, project_dir: Path) -> None:
        write_jsonl(
            project_dir,
            "session.jsonl",
            [
                user_record(session_id="s1", timestamp="2025-04-01T10:00:00Z"),
                assistant_record(session_id="s1", timestamp="2025-04-01T10:00:05Z"),
            ],
        )

        result = parse_conversations([str(project_dir)])
        assert len(result.cwd_accumulators) == 0
