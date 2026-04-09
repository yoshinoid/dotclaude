"""Tests for sync command knowledge upload extension."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dotclaude.commands.sync import _collect_knowledge_items, _upload_knowledge
from dotclaude.utils.api_client import ApiError, AuthRequiredError

# ---------------------------------------------------------------------------
# Fixtures / Helpers
# ---------------------------------------------------------------------------

_PLAIN_RULE = "# Python Rules\n\nUse type hints on all functions.\n"

_FRONTMATTERED_AGENT = """\
---
dc_type: agent
dc_stack:
  - python
dc_scope: global
dc_description: My Python Agent
dc_version: 1
---

# My Python Agent

You are a helpful Python assistant.
"""


def _make_claude_dir(tmp_path: Path) -> Path:
    """Create a minimal ~/.claude-like directory structure."""
    base = tmp_path / ".claude"
    (base / "agents").mkdir(parents=True)
    (base / "rules").mkdir(parents=True)
    (base / "skills" / "my-skill").mkdir(parents=True)
    (base / "commands").mkdir(parents=True)
    return base


# ---------------------------------------------------------------------------
# _collect_knowledge_items
# ---------------------------------------------------------------------------


class TestCollectKnowledgeItems:
    def test_collects_rule_and_agent(self, tmp_path: Path) -> None:
        base = _make_claude_dir(tmp_path)
        (base / "rules" / "python.md").write_text(_PLAIN_RULE, encoding="utf-8")
        (base / "agents" / "helper.md").write_text(_PLAIN_RULE, encoding="utf-8")

        items = _collect_knowledge_items(str(base))

        source_paths = {i["source_path"] for i in items}
        assert "rules/python.md" in source_paths
        assert "agents/helper.md" in source_paths

    def test_item_has_required_keys(self, tmp_path: Path) -> None:
        base = _make_claude_dir(tmp_path)
        (base / "rules" / "test.md").write_text(_PLAIN_RULE, encoding="utf-8")

        items = _collect_knowledge_items(str(base))

        assert len(items) == 1
        item = items[0]
        for key in ("type", "stack", "scope", "title", "description", "content", "content_hash", "source_path"):
            assert key in item, f"Missing key: {key}"

    def test_infers_type_from_path(self, tmp_path: Path) -> None:
        base = _make_claude_dir(tmp_path)
        (base / "rules" / "test.md").write_text(_PLAIN_RULE, encoding="utf-8")
        (base / "agents" / "bot.md").write_text(_PLAIN_RULE, encoding="utf-8")

        items = _collect_knowledge_items(str(base))

        by_path = {i["source_path"]: i for i in items}
        assert by_path["rules/test.md"]["type"] == "rule"
        assert by_path["agents/bot.md"]["type"] == "agent"

    def test_uses_dc_frontmatter_when_present(self, tmp_path: Path) -> None:
        """Files with dc_ frontmatter use those values instead of inference."""
        base = _make_claude_dir(tmp_path)
        (base / "agents" / "python-agent.md").write_text(
            _FRONTMATTERED_AGENT, encoding="utf-8"
        )

        items = _collect_knowledge_items(str(base))

        assert len(items) == 1
        item = items[0]
        # dc_type from frontmatter
        assert item["type"] == "agent"
        # dc_stack from frontmatter
        assert item["stack"] == ["python"]
        # dc_description from frontmatter
        assert item["description"] == "My Python Agent"

    def test_content_hash_is_sha256(self, tmp_path: Path) -> None:
        base = _make_claude_dir(tmp_path)
        (base / "rules" / "test.md").write_text(_PLAIN_RULE, encoding="utf-8")

        items = _collect_knowledge_items(str(base))

        expected_hash = hashlib.sha256(_PLAIN_RULE.encode()).hexdigest()
        assert items[0]["content_hash"] == expected_hash

    def test_same_content_produces_same_hash(self, tmp_path: Path) -> None:
        base = _make_claude_dir(tmp_path)
        (base / "rules" / "a.md").write_text(_PLAIN_RULE, encoding="utf-8")
        (base / "agents" / "b.md").write_text(_PLAIN_RULE, encoding="utf-8")

        items = _collect_knowledge_items(str(base))

        hashes = [i["content_hash"] for i in items]
        assert hashes[0] == hashes[1]

    def test_different_content_produces_different_hash(self, tmp_path: Path) -> None:
        base = _make_claude_dir(tmp_path)
        (base / "rules" / "a.md").write_text("# A\n\nContent A.\n", encoding="utf-8")
        (base / "agents" / "b.md").write_text("# B\n\nContent B.\n", encoding="utf-8")

        items = _collect_knowledge_items(str(base))

        hashes = [i["content_hash"] for i in items]
        assert hashes[0] != hashes[1]

    def test_source_path_is_relative(self, tmp_path: Path) -> None:
        base = _make_claude_dir(tmp_path)
        (base / "rules" / "test.md").write_text(_PLAIN_RULE, encoding="utf-8")

        items = _collect_knowledge_items(str(base))

        # Should be a relative posix path, not absolute
        assert not Path(items[0]["source_path"]).is_absolute()
        assert items[0]["source_path"] == "rules/test.md"

    def test_empty_dir_returns_empty_list(self, tmp_path: Path) -> None:
        base = _make_claude_dir(tmp_path)

        items = _collect_knowledge_items(str(base))

        assert items == []

    def test_non_markdown_files_ignored(self, tmp_path: Path) -> None:
        base = _make_claude_dir(tmp_path)
        (base / "rules" / "ignore.txt").write_text("plain text", encoding="utf-8")
        (base / "rules" / "keep.md").write_text(_PLAIN_RULE, encoding="utf-8")

        items = _collect_knowledge_items(str(base))

        source_paths = {i["source_path"] for i in items}
        assert "rules/ignore.txt" not in source_paths
        assert "rules/keep.md" in source_paths


# ---------------------------------------------------------------------------
# _upload_knowledge
# ---------------------------------------------------------------------------


class TestUploadKnowledge:
    @pytest.fixture
    def sample_items(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "rule",
                "stack": ["python"],
                "scope": "global",
                "title": "Python Rules",
                "description": "Python Rules",
                "content": _PLAIN_RULE,
                "content_hash": hashlib.sha256(_PLAIN_RULE.encode()).hexdigest(),
                "source_path": "rules/python.md",
            }
        ]

    @pytest.mark.asyncio
    async def test_success_returns_response_dict(
        self, sample_items: list[dict[str, Any]]
    ) -> None:
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "uploaded": 1,
            "skipped": 0,
            "chunks_created": 5,
        }

        with patch(
            "dotclaude.commands.sync.api_request",
            new=AsyncMock(return_value=mock_response),
        ):
            result = await _upload_knowledge(sample_items)

        assert result["uploaded"] == 1
        assert result["skipped"] == 0
        assert result["chunks_created"] == 5

    @pytest.mark.asyncio
    async def test_passes_correct_payload(
        self, sample_items: list[dict[str, Any]]
    ) -> None:
        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.json.return_value = {"uploaded": 1, "skipped": 0, "chunks_created": 3}

        mock_request = AsyncMock(return_value=mock_response)
        with patch("dotclaude.commands.sync.api_request", new=mock_request):
            await _upload_knowledge(sample_items)

        call_kwargs = mock_request.call_args
        assert call_kwargs[0][0] == "/api/knowledge/bulk"
        assert call_kwargs[1]["method"] == "POST"
        assert call_kwargs[1]["json_body"] == {"items": sample_items}

    @pytest.mark.asyncio
    async def test_401_raises_api_error(
        self, sample_items: list[dict[str, Any]]
    ) -> None:
        mock_response = MagicMock()
        mock_response.is_success = False
        mock_response.status_code = 401
        mock_response.reason_phrase = "Unauthorized"
        mock_response.json.return_value = {"detail": "Invalid token"}

        with (
            patch(
                "dotclaude.commands.sync.api_request",
                new=AsyncMock(return_value=mock_response),
            ),
            pytest.raises(ApiError) as exc_info,
        ):
            await _upload_knowledge(sample_items)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_500_raises_api_error(
        self, sample_items: list[dict[str, Any]]
    ) -> None:
        mock_response = MagicMock()
        mock_response.is_success = False
        mock_response.status_code = 500
        mock_response.reason_phrase = "Internal Server Error"
        mock_response.json.return_value = {}

        with (
            patch(
                "dotclaude.commands.sync.api_request",
                new=AsyncMock(return_value=mock_response),
            ),
            pytest.raises(ApiError) as exc_info,
        ):
            await _upload_knowledge(sample_items)

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_auth_required_propagates(
        self, sample_items: list[dict[str, Any]]
    ) -> None:
        with (
            patch(
                "dotclaude.commands.sync.api_request",
                new=AsyncMock(side_effect=AuthRequiredError()),
            ),
            pytest.raises(AuthRequiredError),
        ):
            await _upload_knowledge(sample_items)


# ---------------------------------------------------------------------------
# Integration: _do_sync knowledge upload step
# ---------------------------------------------------------------------------


class TestDoSyncKnowledgeIntegration:
    """Verify that the knowledge upload step is called after snapshot sync."""

    @pytest.mark.asyncio
    async def test_knowledge_upload_called_after_snapshot(self, tmp_path: Path) -> None:
        from dotclaude.commands.sync import _do_sync

        base = _make_claude_dir(tmp_path)
        (base / "rules" / "test.md").write_text(_PLAIN_RULE, encoding="utf-8")

        # Mock analyze
        mock_analyze_result = MagicMock()
        mock_analyze_result.model_dump.return_value = {}

        # Mock snapshot sync response
        snapshot_response = MagicMock()
        snapshot_response.is_success = True
        snapshot_response.json.return_value = {"synced_at": "2026-01-01T00:00:00Z"}

        # Mock knowledge upload response
        knowledge_response = MagicMock()
        knowledge_response.is_success = True
        knowledge_response.json.return_value = {
            "uploaded": 1,
            "skipped": 0,
            "chunks_created": 3,
        }

        api_responses = [snapshot_response, knowledge_response]
        call_count = 0

        async def fake_api_request(path: str, **kwargs: Any) -> Any:
            nonlocal call_count
            response = api_responses[call_count]
            call_count += 1
            return response

        with (
            patch("dotclaude.commands.sync.analyze", new=AsyncMock(return_value=mock_analyze_result)),
            patch("dotclaude.commands.sync.api_request", new=fake_api_request),
        ):
            await _do_sync(str(base))

        assert call_count == 2, "Expected exactly 2 API calls (snapshot + knowledge)"

    @pytest.mark.asyncio
    async def test_knowledge_failure_does_not_abort_sync(self, tmp_path: Path) -> None:
        """Snapshot sync should succeed even when knowledge upload fails."""
        from dotclaude.commands.sync import _do_sync

        base = _make_claude_dir(tmp_path)
        (base / "rules" / "test.md").write_text(_PLAIN_RULE, encoding="utf-8")

        mock_analyze_result = MagicMock()
        mock_analyze_result.model_dump.return_value = {}

        snapshot_response = MagicMock()
        snapshot_response.is_success = True
        snapshot_response.json.return_value = {"synced_at": "2026-01-01T00:00:00Z"}

        knowledge_response = MagicMock()
        knowledge_response.is_success = False
        knowledge_response.status_code = 401
        knowledge_response.reason_phrase = "Unauthorized"
        knowledge_response.json.return_value = {"detail": "Unauthorized"}

        api_responses = [snapshot_response, knowledge_response]
        call_count = 0

        async def fake_api_request(path: str, **kwargs: Any) -> Any:
            nonlocal call_count
            response = api_responses[call_count]
            call_count += 1
            return response

        # Should NOT raise even though knowledge upload fails
        with (
            patch("dotclaude.commands.sync.analyze", new=AsyncMock(return_value=mock_analyze_result)),
            patch("dotclaude.commands.sync.api_request", new=fake_api_request),
        ):
            await _do_sync(str(base))  # Must not raise

    @pytest.mark.asyncio
    async def test_no_knowledge_files_skips_upload(self, tmp_path: Path) -> None:
        """When no knowledge files exist, the bulk upload call is skipped."""
        from dotclaude.commands.sync import _do_sync

        base = _make_claude_dir(tmp_path)
        # No markdown files — empty dir

        mock_analyze_result = MagicMock()
        mock_analyze_result.model_dump.return_value = {}

        snapshot_response = MagicMock()
        snapshot_response.is_success = True
        snapshot_response.json.return_value = {"synced_at": "2026-01-01T00:00:00Z"}

        api_call_paths: list[str] = []

        async def fake_api_request(path: str, **kwargs: Any) -> Any:
            api_call_paths.append(path)
            return snapshot_response

        with (
            patch("dotclaude.commands.sync.analyze", new=AsyncMock(return_value=mock_analyze_result)),
            patch("dotclaude.commands.sync.api_request", new=fake_api_request),
        ):
            await _do_sync(str(base))

        assert "/api/knowledge/bulk" not in api_call_paths
