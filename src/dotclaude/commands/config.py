"""Config command — manage dotclaude settings."""

from __future__ import annotations

import os

import typer
from rich.console import Console

from dotclaude.insights.config_store import (
    get_config_file_path,
    read_config,
    write_config,
)

_console = Console()
config_app = typer.Typer(name="config", help="Manage dotclaude configuration")


@config_app.command("set-key")
def set_key(key: str = typer.Argument(..., help="Gemini API key")) -> None:
    """Save Gemini API key for --insights."""
    existing = read_config()
    write_config({**existing, "geminiApiKey": key})
    _console.print(
        f"[green]\u2713[/green] Gemini API key saved to [dim]{get_config_file_path()}[/dim]"
    )
    _console.print("[dim]  Tip: GEMINI_API_KEY env var takes priority over the stored key.[/dim]")


@config_app.command("show")
def show() -> None:
    """Show current configuration."""
    stored = read_config()
    env_key = os.environ.get("GEMINI_API_KEY")

    _console.print("\n[bold]dotclaude config[/bold]\n")

    env_status = (
        f"[green]set[/green] [dim]({env_key[:4]}...)[/dim]"
        if env_key
        else "[dim]not set[/dim]"
    )
    stored_key = stored.get("geminiApiKey")
    file_status = (
        f"[green]set[/green] [dim]({str(stored_key)[:4]}...)[/dim]"
        if stored_key
        else "[dim]not set[/dim]"
    )

    _console.print(f"  GEMINI_API_KEY  (env):   {env_status}")
    _console.print(f"  geminiApiKey    (file):  {file_status}")
    _console.print()
    _console.print(f"  Config file: [dim]{get_config_file_path()}[/dim]")
    _console.print()
