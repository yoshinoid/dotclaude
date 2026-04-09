"""Tests for the team command."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from dotclaude.cli import app
from dotclaude.utils.api_client import ApiError, AuthRequiredError

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


# ---------------------------------------------------------------------------
# team create
# ---------------------------------------------------------------------------


class TestTeamCreate:
    def test_create_success_prints_invite_code(self) -> None:
        """Successful team creation displays the invite code."""
        response = _mock_response(
            json_data={"name": "my-team", "invite_code": "abc123def456"}
        )
        with patch(
            "dotclaude.commands.team.api_request",
            new=AsyncMock(return_value=response),
        ):
            result = runner.invoke(app, ["team", "create", "my-team"])

        assert result.exit_code == 0, result.output
        assert "my-team" in result.output
        assert "abc123def456" in result.output

    def test_create_success_calls_correct_endpoint(self) -> None:
        """team create POSTs to /api/teams with the team name."""
        response = _mock_response(
            json_data={"name": "my-team", "invite_code": "code123"}
        )
        mock_request = AsyncMock(return_value=response)
        with patch("dotclaude.commands.team.api_request", new=mock_request):
            runner.invoke(app, ["team", "create", "my-team"])

        call_args = mock_request.call_args
        assert call_args[0][0] == "/api/teams"
        assert call_args[1]["method"] == "POST"
        assert call_args[1]["json_body"] == {"name": "my-team"}

    def test_create_auth_required_prints_error(self) -> None:
        """team create shows a graceful error when not logged in."""
        with patch(
            "dotclaude.commands.team.api_request",
            new=AsyncMock(side_effect=AuthRequiredError()),
        ):
            result = runner.invoke(app, ["team", "create", "my-team"])

        assert result.exit_code != 0
        assert "Not logged in" in result.output

    def test_create_server_error_prints_error(self) -> None:
        """team create shows a graceful error on server failure."""
        with patch(
            "dotclaude.commands.team.api_request",
            new=AsyncMock(side_effect=ApiError("Internal Server Error", 500)),
        ):
            result = runner.invoke(app, ["team", "create", "my-team"])

        assert result.exit_code != 0
        assert "Internal Server Error" in result.output


# ---------------------------------------------------------------------------
# team join
# ---------------------------------------------------------------------------


class TestTeamJoin:
    def test_join_success_prints_team_info(self) -> None:
        """Successful join displays team name and role."""
        response = _mock_response(
            json_data={"name": "awesome-team", "role": "member"}
        )
        with patch(
            "dotclaude.commands.team.api_request",
            new=AsyncMock(return_value=response),
        ):
            result = runner.invoke(app, ["team", "join", "invitecode99"])

        assert result.exit_code == 0, result.output
        assert "awesome-team" in result.output
        assert "member" in result.output

    def test_join_calls_correct_endpoint(self) -> None:
        """team join POSTs to /api/teams/join with the invite code."""
        response = _mock_response(json_data={"name": "a-team", "role": "member"})
        mock_request = AsyncMock(return_value=response)
        with patch("dotclaude.commands.team.api_request", new=mock_request):
            runner.invoke(app, ["team", "join", "mycode"])

        call_args = mock_request.call_args
        assert call_args[0][0] == "/api/teams/join"
        assert call_args[1]["method"] == "POST"
        assert call_args[1]["json_body"] == {"invite_code": "mycode"}

    def test_join_invalid_code_prints_error(self) -> None:
        """team join shows a graceful error when the code is invalid (404)."""
        with patch(
            "dotclaude.commands.team.api_request",
            new=AsyncMock(side_effect=ApiError("Team not found", 404)),
        ):
            result = runner.invoke(app, ["team", "join", "badcode"])

        assert result.exit_code != 0
        assert "Team not found" in result.output

    def test_join_auth_required_prints_error(self) -> None:
        """team join shows a graceful error when not logged in."""
        with patch(
            "dotclaude.commands.team.api_request",
            new=AsyncMock(side_effect=AuthRequiredError()),
        ):
            result = runner.invoke(app, ["team", "join", "anycode"])

        assert result.exit_code != 0
        assert "Not logged in" in result.output


# ---------------------------------------------------------------------------
# team leave
# ---------------------------------------------------------------------------


class TestTeamLeave:
    def test_leave_success_prints_confirmation(self) -> None:
        """Successful leave prints a confirmation message."""
        response = _mock_response(json_data={"detail": "Left team"})
        with patch(
            "dotclaude.commands.team.api_request",
            new=AsyncMock(return_value=response),
        ):
            result = runner.invoke(app, ["team", "leave", "team-42"])

        assert result.exit_code == 0, result.output
        assert "team-42" in result.output

    def test_leave_calls_correct_endpoint(self) -> None:
        """team leave POSTs to /api/teams/{team_id}/leave."""
        response = _mock_response(json_data={})
        mock_request = AsyncMock(return_value=response)
        with patch("dotclaude.commands.team.api_request", new=mock_request):
            runner.invoke(app, ["team", "leave", "team-99"])

        call_args = mock_request.call_args
        assert call_args[0][0] == "/api/teams/team-99/leave"
        assert call_args[1]["method"] == "POST"

    def test_leave_server_error_prints_error(self) -> None:
        """team leave shows a graceful error on server failure."""
        with patch(
            "dotclaude.commands.team.api_request",
            new=AsyncMock(side_effect=ApiError("Forbidden", 403)),
        ):
            result = runner.invoke(app, ["team", "leave", "team-1"])

        assert result.exit_code != 0
        assert "Forbidden" in result.output


# ---------------------------------------------------------------------------
# team list
# ---------------------------------------------------------------------------


class TestTeamList:
    def test_list_success_renders_table(self) -> None:
        """team list renders a table with team data."""
        teams = [
            {
                "name": "my-team",
                "role": "admin",
                "member_count": 3,
                "invite_code": "abc123def456",
            },
            {
                "name": "other-team",
                "role": "member",
                "member_count": 5,
                "invite_code": None,
            },
        ]
        response = _mock_response(json_data=teams)
        with patch(
            "dotclaude.commands.team.api_request",
            new=AsyncMock(return_value=response),
        ):
            result = runner.invoke(app, ["team", "list"])

        assert result.exit_code == 0, result.output
        assert "my-team" in result.output
        assert "admin" in result.output
        assert "abc123def456" in result.output
        assert "other-team" in result.output
        assert "member" in result.output

    def test_list_empty_teams_prints_no_teams_message(self) -> None:
        """team list prints a friendly message when there are no teams."""
        response = _mock_response(json_data=[])
        with patch(
            "dotclaude.commands.team.api_request",
            new=AsyncMock(return_value=response),
        ):
            result = runner.invoke(app, ["team", "list"])

        assert result.exit_code == 0, result.output
        assert "No teams" in result.output

    def test_list_calls_correct_endpoint(self) -> None:
        """team list sends a GET request to /api/teams."""
        response = _mock_response(json_data=[])
        mock_request = AsyncMock(return_value=response)
        with patch("dotclaude.commands.team.api_request", new=mock_request):
            runner.invoke(app, ["team", "list"])

        call_args = mock_request.call_args
        assert call_args[0][0] == "/api/teams"
        assert call_args[1]["method"] == "GET"

    def test_list_auth_required_prints_error(self) -> None:
        """team list shows a graceful error when not logged in."""
        with patch(
            "dotclaude.commands.team.api_request",
            new=AsyncMock(side_effect=AuthRequiredError()),
        ):
            result = runner.invoke(app, ["team", "list"])

        assert result.exit_code != 0
        assert "Not logged in" in result.output

    def test_list_server_error_prints_error(self) -> None:
        """team list shows a graceful error on server failure."""
        with patch(
            "dotclaude.commands.team.api_request",
            new=AsyncMock(side_effect=ApiError("Service Unavailable", 503)),
        ):
            result = runner.invoke(app, ["team", "list"])

        assert result.exit_code != 0
        assert "Service Unavailable" in result.output


# ---------------------------------------------------------------------------
# Internal helpers (_do_* functions) — async unit tests
# ---------------------------------------------------------------------------


class TestDoCreate:
    @pytest.mark.asyncio
    async def test_success_no_error(self) -> None:
        """_do_create does not raise on success."""
        from dotclaude.commands.team import _do_create

        response = _mock_response(
            json_data={"name": "t", "invite_code": "xyz"}
        )
        with patch(
            "dotclaude.commands.team.api_request",
            new=AsyncMock(return_value=response),
        ):
            await _do_create("t")  # Must not raise

    @pytest.mark.asyncio
    async def test_failure_raises_api_error(self) -> None:
        """_do_create raises ApiError on non-success response."""
        from dotclaude.commands.team import _do_create

        response = _mock_response(
            is_success=False,
            status_code=409,
            reason_phrase="Conflict",
            json_data={"detail": "Team name already taken"},
        )
        with (
            patch(
                "dotclaude.commands.team.api_request",
                new=AsyncMock(return_value=response),
            ),
            pytest.raises(ApiError) as exc_info,
        ):
            await _do_create("duplicate-team")

        assert exc_info.value.status_code == 409


class TestDoJoin:
    @pytest.mark.asyncio
    async def test_failure_404_raises_api_error(self) -> None:
        """_do_join raises ApiError when the invite code is invalid."""
        from dotclaude.commands.team import _do_join

        response = _mock_response(
            is_success=False,
            status_code=404,
            reason_phrase="Not Found",
            json_data={"detail": "Invalid invite code"},
        )
        with (
            patch(
                "dotclaude.commands.team.api_request",
                new=AsyncMock(return_value=response),
            ),
            pytest.raises(ApiError) as exc_info,
        ):
            await _do_join("badcode")

        assert exc_info.value.status_code == 404


class TestDoLeave:
    @pytest.mark.asyncio
    async def test_success_no_error(self) -> None:
        """_do_leave does not raise on success."""
        from dotclaude.commands.team import _do_leave

        response = _mock_response(json_data={})
        with patch(
            "dotclaude.commands.team.api_request",
            new=AsyncMock(return_value=response),
        ):
            await _do_leave("team-1")  # Must not raise


class TestDoList:
    @pytest.mark.asyncio
    async def test_success_no_error(self) -> None:
        """_do_list does not raise on success."""
        from dotclaude.commands.team import _do_list

        response = _mock_response(
            json_data=[{"name": "t", "role": "admin", "member_count": 1, "invite_code": "c"}]
        )
        with patch(
            "dotclaude.commands.team.api_request",
            new=AsyncMock(return_value=response),
        ):
            await _do_list()  # Must not raise

    @pytest.mark.asyncio
    async def test_failure_raises_api_error(self) -> None:
        """_do_list raises ApiError on non-success response."""
        from dotclaude.commands.team import _do_list

        response = _mock_response(
            is_success=False,
            status_code=500,
            reason_phrase="Internal Server Error",
            json_data={},
        )
        with (
            patch(
                "dotclaude.commands.team.api_request",
                new=AsyncMock(return_value=response),
            ),
            pytest.raises(ApiError) as exc_info,
        ):
            await _do_list()

        assert exc_info.value.status_code == 500
