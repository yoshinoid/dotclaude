"""Team command — manage dotclaude teams."""

from __future__ import annotations

import asyncio
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from dotclaude.utils.api_client import ApiError, AuthRequiredError, api_request

_console = Console()
team_app = typer.Typer(name="team", help="Manage dotclaude teams")


async def _do_create(name: str) -> None:
    """POST /api/teams and display the resulting invite code.

    Args:
        name: Team name to create.

    Raises:
        AuthRequiredError: If the user is not logged in.
        ApiError: If the server returns a non-success response.
    """
    res = await api_request("/api/teams", method="POST", json_body={"name": name})

    if not res.is_success:
        try:
            body = res.json()
            detail = body.get("detail", res.reason_phrase)
        except Exception:
            detail = res.reason_phrase
        raise ApiError(detail or "Team creation failed", res.status_code)

    data: dict[str, Any] = res.json()
    invite_code: str = data.get("invite_code", "")
    team_name: str = data.get("name", name)

    _console.print(f"[green]\u2714[/green]  Team [bold]{team_name}[/bold] created.")
    if invite_code:
        _console.print(f"  Invite code: [bold cyan]{invite_code}[/bold cyan]")


async def _do_join(invite_code: str) -> None:
    """POST /api/teams/join and display joined team info.

    Args:
        invite_code: Invite code for the team to join.

    Raises:
        AuthRequiredError: If the user is not logged in.
        ApiError: If the server returns a non-success response.
    """
    res = await api_request(
        "/api/teams/join", method="POST", json_body={"invite_code": invite_code}
    )

    if not res.is_success:
        try:
            body = res.json()
            detail = body.get("detail", res.reason_phrase)
        except Exception:
            detail = res.reason_phrase
        raise ApiError(detail or "Join failed", res.status_code)

    data: dict[str, Any] = res.json()
    team_name: str = data.get("name", "")
    role: str = data.get("role", "member")

    _console.print(f"[green]\u2714[/green]  Joined team [bold]{team_name}[/bold] as [bold]{role}[/bold].")


async def _do_leave(team_id: str) -> None:
    """POST /api/teams/{team_id}/leave.

    Args:
        team_id: ID of the team to leave.

    Raises:
        AuthRequiredError: If the user is not logged in.
        ApiError: If the server returns a non-success response.
    """
    res = await api_request(f"/api/teams/{team_id}/leave", method="POST")

    if not res.is_success:
        try:
            body = res.json()
            detail = body.get("detail", res.reason_phrase)
        except Exception:
            detail = res.reason_phrase
        raise ApiError(detail or "Leave failed", res.status_code)

    _console.print(f"[green]\u2714[/green]  Left team [bold]{team_id}[/bold].")


async def _do_list() -> None:
    """GET /api/teams and display teams in a Rich table.

    Raises:
        AuthRequiredError: If the user is not logged in.
        ApiError: If the server returns a non-success response.
    """
    res = await api_request("/api/teams", method="GET")

    if not res.is_success:
        try:
            body = res.json()
            detail = body.get("detail", res.reason_phrase)
        except Exception:
            detail = res.reason_phrase
        raise ApiError(detail or "List failed", res.status_code)

    data: list[dict[str, Any]] = res.json()

    if not data:
        _console.print("[dim]  No teams found.[/dim]")
        return

    table = Table(title="Teams", show_header=True, header_style="bold")
    table.add_column("Name")
    table.add_column("Role")
    table.add_column("Members", justify="right")
    table.add_column("Invite Code")

    for team in data:
        name: str = team.get("name", "")
        role: str = team.get("role", "")
        members: str = str(team.get("member_count", team.get("members", "-")))
        invite_code: str = team.get("invite_code") or "-"
        table.add_row(name, role, members, invite_code)

    _console.print(table)


def _handle_error(exc: Exception) -> None:
    """Print a graceful error message and exit with code 1.

    Args:
        exc: The exception that was raised.
    """
    _console.print(f"[red]\u2716  {exc}[/red]")
    raise typer.Exit(1) from exc


@team_app.command(name="create")
def team_create(
    name: str = typer.Argument(..., help="Name of the team to create"),
) -> None:
    """Create a new team."""

    async def _run() -> None:
        try:
            await _do_create(name)
        except (AuthRequiredError, ApiError) as e:
            _handle_error(e)
        except Exception as e:
            _handle_error(e)

    asyncio.run(_run())


@team_app.command(name="join")
def team_join(
    code: str = typer.Argument(..., help="Invite code for the team"),
) -> None:
    """Join a team using an invite code."""

    async def _run() -> None:
        try:
            await _do_join(code)
        except (AuthRequiredError, ApiError) as e:
            _handle_error(e)
        except Exception as e:
            _handle_error(e)

    asyncio.run(_run())


@team_app.command(name="leave")
def team_leave(
    team_id: str = typer.Argument(..., help="ID of the team to leave"),
) -> None:
    """Leave a team."""

    async def _run() -> None:
        try:
            await _do_leave(team_id)
        except (AuthRequiredError, ApiError) as e:
            _handle_error(e)
        except Exception as e:
            _handle_error(e)

    asyncio.run(_run())


@team_app.command(name="list")
def team_list() -> None:
    """List all teams you are a member of."""

    async def _run() -> None:
        try:
            await _do_list()
        except (AuthRequiredError, ApiError) as e:
            _handle_error(e)
        except Exception as e:
            _handle_error(e)

    asyncio.run(_run())
