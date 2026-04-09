"""Sync command — parse ~/.claude and push to the dotclaude server."""

from __future__ import annotations

import asyncio

import typer
from rich.console import Console

from dotclaude import __version__ as PACKAGE_VERSION
from dotclaude.parser import analyze
from dotclaude.utils.api_client import ApiError, AuthRequiredError, api_request

_console = Console()
sync_app = typer.Typer(name="sync", help="Sync ~/.claude usage data to the dotclaude server")


async def _do_sync(claude_dir: str | None = None) -> None:
    """Perform a single sync operation."""
    try:
        data = await analyze(claude_dir)
    except Exception as e:
        raise RuntimeError(f"Failed to analyze Claude directory: {e}") from e

    res = await api_request(
        "/api/sync",
        method="POST",
        json_body={"data": data.model_dump(by_alias=True), "client_version": PACKAGE_VERSION},
    )

    if not res.is_success:
        try:
            body = res.json()
            detail = body.get("detail", res.reason_phrase)
        except Exception:
            detail = res.reason_phrase
        raise ApiError(detail or "Sync failed", res.status_code)

    result = res.json()
    synced_at = result.get("synced_at", "")
    try:
        from datetime import datetime

        time_str = datetime.fromisoformat(synced_at.replace("Z", "+00:00")).strftime("%H:%M:%S")
    except Exception:
        time_str = synced_at
    _console.print(f"[green]\u2714[/green]  Synced at {time_str}")


@sync_app.callback(invoke_without_command=True)
def sync(
    path: str = typer.Option(None, "--path", help="Analyze a custom directory"),
    watch: bool = typer.Option(False, "--watch", help="Re-sync automatically every 60 seconds"),
) -> None:
    """Sync ~/.claude usage data to the dotclaude server."""

    async def _run() -> None:
        try:
            await _do_sync(path)
        except AuthRequiredError as e:
            _console.print(f"[red]\u2716  {e}[/red]")
            raise typer.Exit(1) from e
        except Exception as e:
            _console.print(f"[red]\u2716  {e}[/red]")
            raise typer.Exit(1) from e

        if watch:
            import asyncio as _asyncio

            _console.print("[dim]   Watching for changes (every 60s). Ctrl+C to stop.[/dim]")
            while True:
                await _asyncio.sleep(60)
                try:
                    await _do_sync(path)
                except Exception as ex:
                    _console.print(f"[yellow]\u26a0  Sync failed: {ex}[/yellow]")

    asyncio.run(_run())
