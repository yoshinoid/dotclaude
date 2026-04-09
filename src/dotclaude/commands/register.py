"""Register command — create a new account on the dotclaude server."""

from __future__ import annotations

import asyncio
import getpass

import typer
from rich.console import Console

from dotclaude.insights.config_store import get_server_url, read_config, write_config

_console = Console()
register_app = typer.Typer(name="register", help="Create a new dotclaude server account")


@register_app.callback(invoke_without_command=True)
def register(
    server: str = typer.Option(None, "--server", help="Server URL"),
) -> None:
    """Create a new dotclaude server account."""
    server_url = server or get_server_url()

    email = typer.prompt("Email")
    username = typer.prompt("Username")
    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")

    if password != confirm:
        _console.print("[red]\u2716  Passwords do not match.[/red]")
        raise typer.Exit(1)

    async def _do_register() -> None:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(
                    f"{server_url}/api/auth/register",
                    json={"email": email, "username": username, "password": password},
                )
        except Exception as e:
            _console.print(f"[red]\u2716  Connection failed: {e}[/red]")
            raise typer.Exit(1) from e

        if not res.is_success:
            body = res.json() if res.headers.get("content-type", "").startswith("application/json") else {}
            detail = body.get("detail", res.reason_phrase)
            _console.print(f"[red]\u2716  Registration failed: {detail}[/red]")
            raise typer.Exit(1)

        data = res.json()
        config = read_config()
        write_config({
            **config,
            "authToken": data["access_token"],
            "refreshToken": data["refresh_token"],
            "serverUrl": server_url,
        })

        _console.print(f"[green]\u2714[/green]  Account created. Welcome, {username}!")
        _console.print("[dim]   Run: dotclaude sync[/dim]")

    asyncio.run(_do_register())
