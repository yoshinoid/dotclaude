"""Login command — authenticate with the dotclaude server."""

from __future__ import annotations

import asyncio
import getpass

import typer
from rich.console import Console

from dotclaude.insights.config_store import get_server_url, read_config, write_config

_console = Console()
login_app = typer.Typer(name="login", help="Log in to your dotclaude server account")


@login_app.callback(invoke_without_command=True)
def login(
    server: str = typer.Option(None, "--server", help="Server URL"),
) -> None:
    """Log in to your dotclaude server account."""
    server_url = server or get_server_url()

    email = typer.prompt("Email")
    password = getpass.getpass("Password: ")

    async def _do_login() -> None:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(
                    f"{server_url}/api/auth/login",
                    json={"email": email, "password": password},
                )
        except Exception as e:
            _console.print(f"[red]\u2716  Connection failed: {e}[/red]")
            raise typer.Exit(1) from e

        if not res.is_success:
            body = res.json() if res.headers.get("content-type", "").startswith("application/json") else {}
            detail = body.get("detail", res.reason_phrase)
            _console.print(f"[red]\u2716  Login failed: {detail}[/red]")
            raise typer.Exit(1)

        data = res.json()
        config = read_config()
        write_config({
            **config,
            "authToken": data["access_token"],
            "refreshToken": data["refresh_token"],
            "serverUrl": server_url,
        })

        _console.print("[green]\u2714[/green]  Logged in successfully.")
        _console.print(f"[dim]   Server: {server_url}[/dim]")

    asyncio.run(_do_login())
