"""Tests for the workflow-integrated pull commands."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from dotclaude.cli import app
from dotclaude.utils.api_client import ApiError, AuthRequiredError

# ---------------------------------------------------------------------------
# Shared helpers
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


def _make_workflow_run(
    run_id: str = "wf-run-001",
    status: str = "awaiting_approval",
    items: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Build a minimal workflow run JSON dict.

    Args:
        run_id: UUID for the workflow run.
        status: Workflow status string.
        items: List of PullItem dicts to include in output_data.

    Returns:
        JSON-serialisable dict matching the server workflow run schema.
    """
    return {
        "id": run_id,
        "status": status,
        "output_data": {"items": items or []},
    }


def _make_pull_item(
    target_path: str = "rules/backend/python.md",
    content: str = "# Python Rules\n",
    item_type: str = "rule",
    source: str = "recommendation",
) -> dict[str, str]:
    """Build a single PullItem dict (camelCase for JSON).

    Args:
        target_path: Relative path where the file should be written.
        content: File content string.
        item_type: One of rule, agent, skill, command.
        source: One of recommendation, team_standard.

    Returns:
        Dict matching the PullItem JSON schema.
    """
    return {
        "targetPath": target_path,
        "content": content,
        "type": item_type,
        "source": source,
        "knowledgeId": "knowledge-abc-123",
    }


# ---------------------------------------------------------------------------
# --workflow: successful flow (confirm=True)
# ---------------------------------------------------------------------------


class TestWorkflowSuccess:
    def test_workflow_starts_and_applies_on_confirm(self, tmp_path: Path) -> None:
        """--workflow applies files when the user confirms with 'y'."""
        item = _make_pull_item("rules/python.md", "# Python\n")
        run = _make_workflow_run(items=[item])

        mock_request = AsyncMock(return_value=_mock_response(json_data=run))

        with (
            patch("dotclaude.commands.pull.api_request", new=mock_request),
            patch("dotclaude.commands.pull.typer.confirm", return_value=True),
        ):
            result = runner.invoke(app, ["pull", "--workflow", "--path", str(tmp_path)])

        assert result.exit_code == 0, result.output
        written = tmp_path / "rules" / "python.md"
        assert written.exists()
        assert written.read_text() == "# Python\n"

    def test_workflow_calls_recommend_apply_endpoint(self, tmp_path: Path) -> None:
        """--workflow POSTs to /api/workflows/recommend-apply."""
        run = _make_workflow_run(items=[_make_pull_item()])
        mock_request = AsyncMock(return_value=_mock_response(json_data=run))

        with (
            patch("dotclaude.commands.pull.api_request", new=mock_request),
            patch("dotclaude.commands.pull.typer.confirm", return_value=True),
        ):
            runner.invoke(app, ["pull", "--workflow", "--path", str(tmp_path)])

        first_call = mock_request.call_args_list[0]
        assert first_call[0][0] == "/api/workflows/recommend-apply"
        assert first_call[1]["method"] == "POST"

    def test_workflow_calls_approve_on_confirm(self, tmp_path: Path) -> None:
        """--workflow POSTs to /api/workflows/{id}/approve when user confirms."""
        run_id = "wf-run-confirm-001"
        run = _make_workflow_run(run_id=run_id, items=[_make_pull_item()])
        mock_request = AsyncMock(return_value=_mock_response(json_data=run))

        with (
            patch("dotclaude.commands.pull.api_request", new=mock_request),
            patch("dotclaude.commands.pull.typer.confirm", return_value=True),
        ):
            runner.invoke(app, ["pull", "--workflow", "--path", str(tmp_path)])

        paths_called = [c[0][0] for c in mock_request.call_args_list]
        assert any(f"/api/workflows/{run_id}/approve" in p for p in paths_called)

    def test_workflow_shows_preview_table(self, tmp_path: Path) -> None:
        """--workflow prints a preview table before the confirm prompt."""
        item = _make_pull_item("agents/planner.md", item_type="agent")
        run = _make_workflow_run(items=[item])

        with (
            patch("dotclaude.commands.pull.api_request", new=AsyncMock(return_value=_mock_response(json_data=run))),
            patch("dotclaude.commands.pull.typer.confirm", return_value=False),
        ):
            result = runner.invoke(app, ["pull", "--workflow", "--path", str(tmp_path)])

        assert "agents/planner.md" in result.output
        assert "agent" in result.output

    def test_workflow_shows_pull_complete_on_confirm(self, tmp_path: Path) -> None:
        """--workflow prints 'Pull Complete' after files are applied."""
        run = _make_workflow_run(items=[_make_pull_item()])

        with (
            patch("dotclaude.commands.pull.api_request", new=AsyncMock(return_value=_mock_response(json_data=run))),
            patch("dotclaude.commands.pull.typer.confirm", return_value=True),
        ):
            result = runner.invoke(app, ["pull", "--workflow", "--path", str(tmp_path)])

        assert "Pull Complete" in result.output

    def test_workflow_passes_team_id_to_start(self, tmp_path: Path) -> None:
        """--workflow --team passes team_id in the request body."""
        run = _make_workflow_run(items=[])
        mock_request = AsyncMock(return_value=_mock_response(json_data=run))

        with (
            patch("dotclaude.commands.pull.api_request", new=mock_request),
            patch("dotclaude.commands.pull.typer.confirm", return_value=False),
        ):
            runner.invoke(app, ["pull", "--workflow", "--team", "team-99", "--path", str(tmp_path)])

        first_call = mock_request.call_args_list[0]
        assert first_call[1]["json_body"]["team_id"] == "team-99"


# ---------------------------------------------------------------------------
# --workflow: user declines (confirm=False)
# ---------------------------------------------------------------------------


class TestWorkflowRejected:
    def test_workflow_does_not_apply_on_decline(self, tmp_path: Path) -> None:
        """--workflow must not write any files when the user declines."""
        item = _make_pull_item("rules/python.md")
        run = _make_workflow_run(items=[item])

        with (
            patch("dotclaude.commands.pull.api_request", new=AsyncMock(return_value=_mock_response(json_data=run))),
            patch("dotclaude.commands.pull.typer.confirm", return_value=False),
        ):
            result = runner.invoke(app, ["pull", "--workflow", "--path", str(tmp_path)])

        assert result.exit_code == 0, result.output
        assert not (tmp_path / "rules" / "python.md").exists()

    def test_workflow_calls_reject_on_decline(self, tmp_path: Path) -> None:
        """--workflow POSTs to /api/workflows/{id}/reject when user declines."""
        run_id = "wf-run-decline-001"
        run = _make_workflow_run(run_id=run_id, items=[_make_pull_item()])
        mock_request = AsyncMock(return_value=_mock_response(json_data=run))

        with (
            patch("dotclaude.commands.pull.api_request", new=mock_request),
            patch("dotclaude.commands.pull.typer.confirm", return_value=False),
        ):
            runner.invoke(app, ["pull", "--workflow", "--path", str(tmp_path)])

        paths_called = [c[0][0] for c in mock_request.call_args_list]
        assert any(f"/api/workflows/{run_id}/reject" in p for p in paths_called)

    def test_workflow_prints_cancelled_on_decline(self, tmp_path: Path) -> None:
        """--workflow prints 'Cancelled' when the user declines."""
        run = _make_workflow_run(items=[_make_pull_item()])

        with (
            patch("dotclaude.commands.pull.api_request", new=AsyncMock(return_value=_mock_response(json_data=run))),
            patch("dotclaude.commands.pull.typer.confirm", return_value=False),
        ):
            result = runner.invoke(app, ["pull", "--workflow", "--path", str(tmp_path)])

        assert "Cancelled" in result.output

    def test_workflow_no_items_skips_confirm(self, tmp_path: Path) -> None:
        """--workflow with empty output_data skips the confirm prompt entirely."""
        run = _make_workflow_run(items=[])
        confirm_mock = MagicMock()

        with (
            patch("dotclaude.commands.pull.api_request", new=AsyncMock(return_value=_mock_response(json_data=run))),
            patch("dotclaude.commands.pull.typer.confirm", new=confirm_mock),
        ):
            result = runner.invoke(app, ["pull", "--workflow", "--path", str(tmp_path)])

        assert result.exit_code == 0, result.output
        confirm_mock.assert_not_called()


# ---------------------------------------------------------------------------
# --approve
# ---------------------------------------------------------------------------


class TestApprove:
    def test_approve_applies_files(self, tmp_path: Path) -> None:
        """--approve <id> applies files from the workflow output_data."""
        item = _make_pull_item("rules/python.md", "# Approved\n")
        run = _make_workflow_run(run_id="wf-approve-001", items=[item])

        with patch(
            "dotclaude.commands.pull.api_request",
            new=AsyncMock(return_value=_mock_response(json_data=run)),
        ):
            result = runner.invoke(
                app, ["pull", "--approve", "wf-approve-001", "--path", str(tmp_path)]
            )

        assert result.exit_code == 0, result.output
        written = tmp_path / "rules" / "python.md"
        assert written.exists()
        assert written.read_text() == "# Approved\n"

    def test_approve_calls_approve_endpoint(self, tmp_path: Path) -> None:
        """--approve POSTs to /api/workflows/{id}/approve."""
        run_id = "wf-approve-002"
        run = _make_workflow_run(run_id=run_id, items=[_make_pull_item()])
        mock_request = AsyncMock(return_value=_mock_response(json_data=run))

        with patch("dotclaude.commands.pull.api_request", new=mock_request):
            runner.invoke(app, ["pull", "--approve", run_id, "--path", str(tmp_path)])

        paths_called = [c[0][0] for c in mock_request.call_args_list]
        assert any(f"/api/workflows/{run_id}/approve" in p for p in paths_called)

    def test_approve_shows_pull_complete(self, tmp_path: Path) -> None:
        """--approve prints 'Pull Complete' after files are applied."""
        run = _make_workflow_run(items=[_make_pull_item()])

        with patch(
            "dotclaude.commands.pull.api_request",
            new=AsyncMock(return_value=_mock_response(json_data=run)),
        ):
            result = runner.invoke(
                app, ["pull", "--approve", "wf-any", "--path", str(tmp_path)]
            )

        assert "Pull Complete" in result.output

    def test_approve_no_items_prints_message(self, tmp_path: Path) -> None:
        """--approve with empty output_data prints an informational message."""
        run = _make_workflow_run(items=[])

        with patch(
            "dotclaude.commands.pull.api_request",
            new=AsyncMock(return_value=_mock_response(json_data=run)),
        ):
            result = runner.invoke(
                app, ["pull", "--approve", "wf-empty", "--path", str(tmp_path)]
            )

        assert result.exit_code == 0, result.output
        assert "no files" in result.output.lower()


# ---------------------------------------------------------------------------
# --reject
# ---------------------------------------------------------------------------


class TestReject:
    def test_reject_calls_reject_endpoint(self, tmp_path: Path) -> None:
        """--reject POSTs to /api/workflows/{id}/reject."""
        run_id = "wf-reject-001"
        mock_request = AsyncMock(return_value=_mock_response(json_data={}))

        with patch("dotclaude.commands.pull.api_request", new=mock_request):
            result = runner.invoke(app, ["pull", "--reject", run_id])

        assert result.exit_code == 0, result.output
        first_call = mock_request.call_args_list[0]
        assert first_call[0][0] == f"/api/workflows/{run_id}/reject"
        assert first_call[1]["method"] == "POST"

    def test_reject_prints_confirmation(self, tmp_path: Path) -> None:
        """--reject prints a confirmation message."""
        with patch(
            "dotclaude.commands.pull.api_request",
            new=AsyncMock(return_value=_mock_response(json_data={})),
        ):
            result = runner.invoke(app, ["pull", "--reject", "wf-reject-002"])

        assert result.exit_code == 0, result.output
        assert "rejected" in result.output.lower()

    def test_reject_does_not_write_files(self, tmp_path: Path) -> None:
        """--reject must never write any files to disk."""
        with patch(
            "dotclaude.commands.pull.api_request",
            new=AsyncMock(return_value=_mock_response(json_data={})),
        ):
            runner.invoke(app, ["pull", "--reject", "wf-any", "--path", str(tmp_path)])

        assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------------------
# --status
# ---------------------------------------------------------------------------


class TestStatus:
    def test_status_shows_run_id_and_status(self) -> None:
        """--status displays the run ID and current status."""
        run_id = "wf-status-001"
        run = _make_workflow_run(run_id=run_id, status="awaiting_approval", items=[])

        with patch(
            "dotclaude.commands.pull.api_request",
            new=AsyncMock(return_value=_mock_response(json_data=run)),
        ):
            result = runner.invoke(app, ["pull", "--status", run_id])

        assert result.exit_code == 0, result.output
        assert run_id in result.output
        assert "awaiting_approval" in result.output

    def test_status_shows_items_preview(self) -> None:
        """--status shows a file preview when output_data contains items."""
        run_id = "wf-status-002"
        item = _make_pull_item("agents/planner.md", item_type="agent")
        run = _make_workflow_run(run_id=run_id, items=[item])

        with patch(
            "dotclaude.commands.pull.api_request",
            new=AsyncMock(return_value=_mock_response(json_data=run)),
        ):
            result = runner.invoke(app, ["pull", "--status", run_id])

        assert "agents/planner.md" in result.output
        assert "agent" in result.output

    def test_status_calls_get_workflow_endpoint(self) -> None:
        """--status GETs /api/workflows/{id}."""
        run_id = "wf-status-003"
        mock_request = AsyncMock(
            return_value=_mock_response(json_data=_make_workflow_run(run_id=run_id))
        )

        with patch("dotclaude.commands.pull.api_request", new=mock_request):
            runner.invoke(app, ["pull", "--status", run_id])

        call_args = mock_request.call_args_list[0]
        assert call_args[0][0] == f"/api/workflows/{run_id}"
        assert call_args[1]["method"] == "GET"

    def test_status_empty_output_data_prints_no_items_message(self) -> None:
        """--status with empty output_data prints an informational message."""
        run = _make_workflow_run(run_id="wf-empty", items=[])

        with patch(
            "dotclaude.commands.pull.api_request",
            new=AsyncMock(return_value=_mock_response(json_data=run)),
        ):
            result = runner.invoke(app, ["pull", "--status", "wf-empty"])

        assert result.exit_code == 0, result.output
        assert "No items" in result.output


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestWorkflowErrors:
    def test_server_failure_on_start_prints_error(self, tmp_path: Path) -> None:
        """--workflow prints 'Pull failed' when the start API call fails."""
        with (
            patch(
                "dotclaude.commands.pull.api_request",
                new=AsyncMock(side_effect=ApiError("Internal Server Error", 500)),
            ),
            patch("dotclaude.commands.pull.typer.confirm", return_value=True),
        ):
            result = runner.invoke(
                app, ["pull", "--workflow", "--path", str(tmp_path)]
            )

        assert result.exit_code != 0
        assert "Pull failed" in result.output
        assert "Internal Server Error" in result.output

    def test_server_failure_on_approve_prints_error(self, tmp_path: Path) -> None:
        """--approve prints 'Pull failed' when the approve API call fails."""
        with patch(
            "dotclaude.commands.pull.api_request",
            new=AsyncMock(side_effect=ApiError("Service Unavailable", 503)),
        ):
            result = runner.invoke(
                app, ["pull", "--approve", "wf-fail", "--path", str(tmp_path)]
            )

        assert result.exit_code != 0
        assert "Pull failed" in result.output

    def test_server_failure_on_reject_prints_error(self) -> None:
        """--reject prints 'Pull failed' when the reject API call fails."""
        with patch(
            "dotclaude.commands.pull.api_request",
            new=AsyncMock(side_effect=ApiError("Not Found", 404)),
        ):
            result = runner.invoke(app, ["pull", "--reject", "wf-fail"])

        assert result.exit_code != 0
        assert "Pull failed" in result.output

    def test_server_failure_on_status_prints_error(self) -> None:
        """--status prints 'Pull failed' when the fetch API call fails."""
        with patch(
            "dotclaude.commands.pull.api_request",
            new=AsyncMock(side_effect=ApiError("Not Found", 404)),
        ):
            result = runner.invoke(app, ["pull", "--status", "wf-fail"])

        assert result.exit_code != 0
        assert "Pull failed" in result.output

    def test_auth_required_on_workflow_start(self, tmp_path: Path) -> None:
        """--workflow shows a login prompt when not authenticated."""
        with (
            patch(
                "dotclaude.commands.pull.api_request",
                new=AsyncMock(side_effect=AuthRequiredError()),
            ),
            patch("dotclaude.commands.pull.typer.confirm", return_value=True),
        ):
            result = runner.invoke(
                app, ["pull", "--workflow", "--path", str(tmp_path)]
            )

        assert result.exit_code != 0
        assert "로그인이 필요합니다" in result.output

    def test_auth_required_on_approve(self, tmp_path: Path) -> None:
        """--approve shows a login prompt when not authenticated."""
        with patch(
            "dotclaude.commands.pull.api_request",
            new=AsyncMock(side_effect=AuthRequiredError()),
        ):
            result = runner.invoke(
                app, ["pull", "--approve", "wf-any", "--path", str(tmp_path)]
            )

        assert result.exit_code != 0
        assert "로그인이 필요합니다" in result.output

    def test_non_success_response_on_workflow_start(self, tmp_path: Path) -> None:
        """--workflow raises on non-success HTTP response from server."""
        bad_response = _mock_response(
            is_success=False,
            status_code=500,
            reason_phrase="Internal Server Error",
            json_data={"detail": "Temporarily unavailable"},
        )
        with (
            patch(
                "dotclaude.commands.pull.api_request",
                new=AsyncMock(return_value=bad_response),
            ),
            patch("dotclaude.commands.pull.typer.confirm", return_value=True),
        ):
            result = runner.invoke(
                app, ["pull", "--workflow", "--path", str(tmp_path)]
            )

        assert result.exit_code != 0
        assert "Pull failed" in result.output


# ---------------------------------------------------------------------------
# Internal async unit tests
# ---------------------------------------------------------------------------


class TestDoWorkflow:
    @pytest.mark.asyncio
    async def test_do_workflow_applies_items_on_confirm(self, tmp_path: Path) -> None:
        """_do_workflow writes files when typer.confirm returns True."""
        from dotclaude.commands.pull import _do_workflow

        item = _make_pull_item("rules/test.md", "# Test\n")
        run = _make_workflow_run(items=[item])

        with (
            patch(
                "dotclaude.commands.pull.api_request",
                new=AsyncMock(return_value=_mock_response(json_data=run)),
            ),
            patch("dotclaude.commands.pull.typer.confirm", return_value=True),
        ):
            await _do_workflow(team_id=None, base_dir=tmp_path)

        assert (tmp_path / "rules" / "test.md").exists()

    @pytest.mark.asyncio
    async def test_do_workflow_does_not_apply_on_decline(self, tmp_path: Path) -> None:
        """_do_workflow does not write files when typer.confirm returns False."""
        from dotclaude.commands.pull import _do_workflow

        item = _make_pull_item("rules/test.md", "# Test\n")
        run = _make_workflow_run(items=[item])

        with (
            patch(
                "dotclaude.commands.pull.api_request",
                new=AsyncMock(return_value=_mock_response(json_data=run)),
            ),
            patch("dotclaude.commands.pull.typer.confirm", return_value=False),
        ):
            await _do_workflow(team_id=None, base_dir=tmp_path)

        assert not (tmp_path / "rules" / "test.md").exists()

    @pytest.mark.asyncio
    async def test_do_workflow_propagates_api_error(self, tmp_path: Path) -> None:
        """_do_workflow propagates ApiError from _start_workflow."""
        from dotclaude.commands.pull import _do_workflow

        with (
            patch(
                "dotclaude.commands.pull.api_request",
                new=AsyncMock(side_effect=ApiError("Server Error", 500)),
            ),
            patch("dotclaude.commands.pull.typer.confirm", return_value=True),
            pytest.raises(ApiError),
        ):
            await _do_workflow(team_id=None, base_dir=tmp_path)


class TestDoApprove:
    @pytest.mark.asyncio
    async def test_do_approve_writes_items(self, tmp_path: Path) -> None:
        """_do_approve writes files returned by the workflow."""
        from dotclaude.commands.pull import _do_approve

        item = _make_pull_item("agents/planner.md", "# Planner\n")
        run = _make_workflow_run(items=[item])

        with patch(
            "dotclaude.commands.pull.api_request",
            new=AsyncMock(return_value=_mock_response(json_data=run)),
        ):
            await _do_approve("wf-test", tmp_path)

        assert (tmp_path / "agents" / "planner.md").exists()

    @pytest.mark.asyncio
    async def test_do_approve_propagates_auth_error(self, tmp_path: Path) -> None:
        """_do_approve propagates AuthRequiredError."""
        from dotclaude.commands.pull import _do_approve

        with (
            patch(
                "dotclaude.commands.pull.api_request",
                new=AsyncMock(side_effect=AuthRequiredError()),
            ),
            pytest.raises(AuthRequiredError),
        ):
            await _do_approve("wf-test", tmp_path)


class TestDoReject:
    @pytest.mark.asyncio
    async def test_do_reject_does_not_raise_on_success(self) -> None:
        """_do_reject does not raise when the server returns success."""
        from dotclaude.commands.pull import _do_reject

        with patch(
            "dotclaude.commands.pull.api_request",
            new=AsyncMock(return_value=_mock_response(json_data={})),
        ):
            await _do_reject("wf-test")  # Must not raise

    @pytest.mark.asyncio
    async def test_do_reject_propagates_api_error(self) -> None:
        """_do_reject propagates ApiError on failure."""
        from dotclaude.commands.pull import _do_reject

        with (
            patch(
                "dotclaude.commands.pull.api_request",
                new=AsyncMock(side_effect=ApiError("Not Found", 404)),
            ),
            pytest.raises(ApiError),
        ):
            await _do_reject("wf-test")


class TestDoStatus:
    @pytest.mark.asyncio
    async def test_do_status_does_not_raise_on_success(self) -> None:
        """_do_status does not raise when the server returns valid data."""
        from dotclaude.commands.pull import _do_status

        run = _make_workflow_run(run_id="wf-ok", status="completed", items=[])

        with patch(
            "dotclaude.commands.pull.api_request",
            new=AsyncMock(return_value=_mock_response(json_data=run)),
        ):
            await _do_status("wf-ok")  # Must not raise

    @pytest.mark.asyncio
    async def test_do_status_propagates_api_error(self) -> None:
        """_do_status propagates ApiError on failure."""
        from dotclaude.commands.pull import _do_status

        with (
            patch(
                "dotclaude.commands.pull.api_request",
                new=AsyncMock(side_effect=ApiError("Not Found", 404)),
            ),
            pytest.raises(ApiError),
        ):
            await _do_status("wf-missing")
