"""Tests for the pull command and safe_write utility."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from dotclaude.cli import app
from dotclaude.utils.api_client import ApiError, AuthRequiredError
from dotclaude.utils.file_writer import safe_write

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

runner = CliRunner()


def _mock_response(
    *,
    is_success: bool = True,
    status_code: int = 200,
    json_data: object = None,
    reason_phrase: str = "OK",
) -> MagicMock:
    """Build a fake httpx.Response-like mock.

    Args:
        is_success: Whether the response is considered successful.
        status_code: HTTP status code.
        json_data: Data returned by .json().
        reason_phrase: Human-readable HTTP reason phrase.

    Returns:
        A configured MagicMock resembling an httpx.Response.
    """
    mock = MagicMock()
    mock.is_success = is_success
    mock.status_code = status_code
    mock.reason_phrase = reason_phrase
    mock.json.return_value = json_data if json_data is not None else {}
    return mock


def _pull_package_json(
    items: list[dict[str, str]] | None = None,
    team_name: str | None = None,
) -> dict[str, object]:
    """Build a minimal PullPackage JSON dict.

    Args:
        items: List of PullItem dicts to include in the package.
        team_name: Optional team name field.

    Returns:
        JSON-serialisable dict matching the PullPackage schema.
    """
    return {
        "items": items or [],
        "teamName": team_name,
        "generatedAt": "2026-04-09T00:00:00Z",
    }


def _make_item(
    target_path: str = "rules/backend/python.md",
    content: str = "# Python Rules\n",
    item_type: str = "rule",
    source: str = "recommendation",
) -> dict[str, str]:
    """Construct a single PullItem dict.

    Args:
        target_path: Relative path where the file should be written.
        content: File content.
        item_type: One of rule, agent, skill, command.
        source: One of recommendation, team_standard.

    Returns:
        Dict matching the PullItem schema (camelCase for JSON).
    """
    return {
        "targetPath": target_path,
        "content": content,
        "type": item_type,
        "source": source,
        "knowledgeId": "knowledge-abc-123",
    }


# ---------------------------------------------------------------------------
# safe_write unit tests
# ---------------------------------------------------------------------------


class TestSafeWrite:
    def test_new_file_returns_created(self, tmp_path: Path) -> None:
        """safe_write returns 'created' when the target file does not exist."""
        action = safe_write(tmp_path, "rules/python.md", "# content\n")
        assert action == "created"
        assert (tmp_path / "rules" / "python.md").read_text() == "# content\n"

    def test_new_file_creates_parent_directories(self, tmp_path: Path) -> None:
        """safe_write creates all missing parent directories automatically."""
        safe_write(tmp_path, "a/b/c/deep.md", "deep content")
        assert (tmp_path / "a" / "b" / "c" / "deep.md").exists()

    def test_existing_file_returns_updated(self, tmp_path: Path) -> None:
        """safe_write returns 'updated' when the target file already exists."""
        target = tmp_path / "existing.md"
        target.write_text("old content", encoding="utf-8")

        action = safe_write(tmp_path, "existing.md", "new content")
        assert action == "updated"

    def test_existing_file_creates_bak(self, tmp_path: Path) -> None:
        """safe_write creates a .bak.{timestamp} backup of an existing file."""
        target = tmp_path / "existing.md"
        target.write_text("original", encoding="utf-8")

        before = int(time.time())
        safe_write(tmp_path, "existing.md", "updated")
        after = int(time.time())

        bak_files = list(tmp_path.glob("existing.md.bak.*"))
        assert len(bak_files) == 1, "Expected exactly one backup file"

        bak_ts = int(bak_files[0].name.split(".bak.")[-1])
        assert before <= bak_ts <= after, "Backup timestamp should be within test window"
        assert bak_files[0].read_text() == "original"

    def test_existing_file_overwrites_with_new_content(self, tmp_path: Path) -> None:
        """safe_write writes the new content to the original path."""
        target = tmp_path / "file.md"
        target.write_text("old", encoding="utf-8")

        safe_write(tmp_path, "file.md", "new")
        assert target.read_text() == "new"

    def test_path_traversal_raises_value_error(self, tmp_path: Path) -> None:
        """safe_write raises ValueError for paths that escape base_dir."""
        with pytest.raises(ValueError, match="Path traversal blocked"):
            safe_write(tmp_path, "../outside.md", "evil content")

    def test_absolute_path_traversal_raises_value_error(self, tmp_path: Path) -> None:
        """safe_write raises ValueError for absolute paths outside base_dir."""
        with pytest.raises(ValueError, match="Path traversal blocked"):
            safe_write(tmp_path, "/etc/passwd", "evil content")


# ---------------------------------------------------------------------------
# pull CLI integration tests
# ---------------------------------------------------------------------------


class TestPullSuccess:
    def test_pull_creates_files(self, tmp_path: Path) -> None:
        """dotclaude pull applies files to disk when server returns items."""
        items = [_make_item("rules/backend/python.md", "# Python\n")]
        response = _mock_response(json_data=_pull_package_json(items=items))

        with patch(
            "dotclaude.commands.pull.api_request",
            new=AsyncMock(return_value=response),
        ):
            result = runner.invoke(app, ["pull", "--path", str(tmp_path)])

        assert result.exit_code == 0, result.output
        written = tmp_path / "rules" / "backend" / "python.md"
        assert written.exists()
        assert written.read_text() == "# Python\n"

    def test_pull_shows_complete_message(self, tmp_path: Path) -> None:
        """dotclaude pull prints the Pull Complete summary after applying."""
        items = [_make_item("rules/python.md")]
        response = _mock_response(json_data=_pull_package_json(items=items))

        with patch(
            "dotclaude.commands.pull.api_request",
            new=AsyncMock(return_value=response),
        ):
            result = runner.invoke(app, ["pull", "--path", str(tmp_path)])

        assert result.exit_code == 0, result.output
        assert "Pull Complete" in result.output

    def test_pull_shows_item_type_and_path(self, tmp_path: Path) -> None:
        """dotclaude pull table includes file type and target path."""
        items = [_make_item("agents/planner.md", item_type="agent")]
        response = _mock_response(json_data=_pull_package_json(items=items))

        with patch(
            "dotclaude.commands.pull.api_request",
            new=AsyncMock(return_value=response),
        ):
            result = runner.invoke(app, ["pull", "--path", str(tmp_path)])

        assert "agent" in result.output
        assert "agents/planner.md" in result.output


class TestPullDryRun:
    def test_dry_run_does_not_write_files(self, tmp_path: Path) -> None:
        """dotclaude pull --dry-run must not write any files."""
        items = [_make_item("rules/backend/python.md")]
        response = _mock_response(json_data=_pull_package_json(items=items))

        with patch(
            "dotclaude.commands.pull.api_request",
            new=AsyncMock(return_value=response),
        ):
            result = runner.invoke(app, ["pull", "--dry-run", "--path", str(tmp_path)])

        assert result.exit_code == 0, result.output
        assert not (tmp_path / "rules" / "backend" / "python.md").exists()

    def test_dry_run_shows_preview_header(self, tmp_path: Path) -> None:
        """dotclaude pull --dry-run prints a preview table header."""
        items = [_make_item("rules/python.md")]
        response = _mock_response(json_data=_pull_package_json(items=items))

        with patch(
            "dotclaude.commands.pull.api_request",
            new=AsyncMock(return_value=response),
        ):
            result = runner.invoke(app, ["pull", "--dry-run", "--path", str(tmp_path)])

        assert "Pull Preview" in result.output
        assert "Run without --dry-run" in result.output

    def test_dry_run_shows_source_column(self, tmp_path: Path) -> None:
        """dotclaude pull --dry-run table includes the source column."""
        items = [_make_item("agents/planner.md", source="team_standard")]
        response = _mock_response(json_data=_pull_package_json(items=items))

        with patch(
            "dotclaude.commands.pull.api_request",
            new=AsyncMock(return_value=response),
        ):
            result = runner.invoke(app, ["pull", "--dry-run", "--path", str(tmp_path)])

        assert "team_standard" in result.output


class TestPullTeamFlag:
    def test_pull_team_sends_team_id_param(self, tmp_path: Path) -> None:
        """dotclaude pull --team passes team_id as a query parameter."""
        response = _mock_response(json_data=_pull_package_json(items=[]))
        mock_request = AsyncMock(return_value=response)

        with patch("dotclaude.commands.pull.api_request", new=mock_request):
            runner.invoke(app, ["pull", "--team", "team-42", "--path", str(tmp_path)])

        call_path: str = mock_request.call_args[0][0]
        assert "team_id=team-42" in call_path

    def test_pull_without_team_does_not_include_team_id(self, tmp_path: Path) -> None:
        """dotclaude pull without --team does not send a team_id query param."""
        response = _mock_response(json_data=_pull_package_json(items=[]))
        mock_request = AsyncMock(return_value=response)

        with patch("dotclaude.commands.pull.api_request", new=mock_request):
            runner.invoke(app, ["pull", "--path", str(tmp_path)])

        call_path: str = mock_request.call_args[0][0]
        assert "team_id" not in call_path


class TestPullEdgeCases:
    def test_empty_package_prints_no_files_message(self, tmp_path: Path) -> None:
        """dotclaude pull prints 'No files to pull' when the server returns nothing."""
        response = _mock_response(json_data=_pull_package_json(items=[]))

        with patch(
            "dotclaude.commands.pull.api_request",
            new=AsyncMock(return_value=response),
        ):
            result = runner.invoke(app, ["pull", "--path", str(tmp_path)])

        assert result.exit_code == 0, result.output
        assert "No files to pull" in result.output

    def test_updated_file_shows_backup_in_output(self, tmp_path: Path) -> None:
        """dotclaude pull shows backup filename in table when a file is overwritten."""
        existing = tmp_path / "rules" / "python.md"
        existing.parent.mkdir(parents=True)
        existing.write_text("old content", encoding="utf-8")

        items = [_make_item("rules/python.md", content="new content")]
        response = _mock_response(json_data=_pull_package_json(items=items))

        with patch(
            "dotclaude.commands.pull.api_request",
            new=AsyncMock(return_value=response),
        ):
            result = runner.invoke(app, ["pull", "--path", str(tmp_path)])

        assert result.exit_code == 0, result.output
        assert "backup" in result.output
        assert existing.read_text() == "new content"

    def test_path_traversal_item_is_skipped(self, tmp_path: Path) -> None:
        """Items with traversal paths are skipped with a warning, not crash."""
        items = [
            _make_item("../evil.md", content="bad"),
            _make_item("rules/safe.md", content="good"),
        ]
        response = _mock_response(json_data=_pull_package_json(items=items))

        with patch(
            "dotclaude.commands.pull.api_request",
            new=AsyncMock(return_value=response),
        ):
            result = runner.invoke(app, ["pull", "--path", str(tmp_path)])

        assert result.exit_code == 0, result.output
        assert "Skipped" in result.output
        # The safe file must still be written
        assert (tmp_path / "rules" / "safe.md").exists()
        # The traversal file must NOT exist
        assert not (tmp_path.parent / "evil.md").exists()


class TestPullErrors:
    def test_server_failure_prints_error(self, tmp_path: Path) -> None:
        """dotclaude pull prints 'Pull failed' on API error."""
        with patch(
            "dotclaude.commands.pull.api_request",
            new=AsyncMock(side_effect=ApiError("Internal Server Error", 500)),
        ):
            result = runner.invoke(app, ["pull", "--path", str(tmp_path)])

        assert result.exit_code != 0
        assert "Pull failed" in result.output
        assert "Internal Server Error" in result.output

    def test_auth_required_prints_login_message(self, tmp_path: Path) -> None:
        """dotclaude pull prints a login prompt when not authenticated."""
        with patch(
            "dotclaude.commands.pull.api_request",
            new=AsyncMock(side_effect=AuthRequiredError()),
        ):
            result = runner.invoke(app, ["pull", "--path", str(tmp_path)])

        assert result.exit_code != 0
        assert "로그인이 필요합니다" in result.output

    def test_server_non_success_response_prints_error(self, tmp_path: Path) -> None:
        """dotclaude pull raises on non-success HTTP responses."""
        response = _mock_response(
            is_success=False,
            status_code=503,
            reason_phrase="Service Unavailable",
            json_data={"detail": "Temporarily unavailable"},
        )
        with patch(
            "dotclaude.commands.pull.api_request",
            new=AsyncMock(return_value=response),
        ):
            result = runner.invoke(app, ["pull", "--path", str(tmp_path)])

        assert result.exit_code != 0
        assert "Pull failed" in result.output


# ---------------------------------------------------------------------------
# Internal async helper unit tests
# ---------------------------------------------------------------------------


class TestDoPull:
    @pytest.mark.asyncio
    async def test_do_pull_no_items_returns_without_writing(
        self, tmp_path: Path
    ) -> None:
        """_do_pull does not write any files when package is empty."""
        from dotclaude.commands.pull import _do_pull

        response = _mock_response(json_data=_pull_package_json(items=[]))
        with patch(
            "dotclaude.commands.pull.api_request",
            new=AsyncMock(return_value=response),
        ):
            await _do_pull(team_id=None, dry_run=False, base_dir=tmp_path)

        assert list(tmp_path.iterdir()) == []

    @pytest.mark.asyncio
    async def test_do_pull_dry_run_does_not_write(self, tmp_path: Path) -> None:
        """_do_pull with dry_run=True must never write files."""
        from dotclaude.commands.pull import _do_pull

        items = [_make_item("rules/test.md", content="# test")]
        response = _mock_response(json_data=_pull_package_json(items=items))

        with patch(
            "dotclaude.commands.pull.api_request",
            new=AsyncMock(return_value=response),
        ):
            await _do_pull(team_id=None, dry_run=True, base_dir=tmp_path)

        assert not (tmp_path / "rules" / "test.md").exists()

    @pytest.mark.asyncio
    async def test_do_pull_auth_error_propagates(self, tmp_path: Path) -> None:
        """_do_pull propagates AuthRequiredError from api_request."""
        from dotclaude.commands.pull import _do_pull

        with (
            patch(
                "dotclaude.commands.pull.api_request",
                new=AsyncMock(side_effect=AuthRequiredError()),
            ),
            pytest.raises(AuthRequiredError),
        ):
            await _do_pull(team_id=None, dry_run=False, base_dir=tmp_path)
