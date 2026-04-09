"""Analyze command — the default dotclaude command."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer
from dotclaude_types.models import AnalyzeOptions
from rich.console import Console

from dotclaude.display.dashboard import render_dashboard
from dotclaude.display.html_report import render_html
from dotclaude.parser import analyze

_err_console = Console(stderr=True)


def run_analyze(
    path: str | None = None,
    json_output: bool = False,
    since: str | None = None,
    until: str | None = None,
    top: int | None = None,
    html: str | None = None,
) -> None:
    """Run the analyze command.

    Args:
        path: Custom path to ~/.claude directory.
        json_output: Output raw JSON instead of the dashboard.
        since: Include only records on or after this date (YYYY-MM-DD).
        until: Include only records on or before this date (YYYY-MM-DD).
        top: Max items per section in the dashboard.
        html: Export as HTML file (path).
    """
    _err_console.print("[dim]Analyzing ~/.claude...[/dim]", end="\r")

    try:
        data = asyncio.run(
            analyze(
                AnalyzeOptions(
                    claude_dir=path,
                    since=since,
                    until=until,
                    top=top,
                )
            )
        )
    except Exception as e:
        _err_console.print(f"[red]Error:[/red] Failed to analyze Claude directory.\n  {e}")
        _err_console.print(
            "\n[dim]Tip: Ensure ~/.claude exists and contains Claude Code session data.[/dim]"
        )
        if path is not None:
            _err_console.print(f"[dim]  Custom path used: {path}[/dim]")
        raise typer.Exit(1) from e

    _err_console.print("                          ", end="\r")  # clear spinner line

    if json_output:
        print(json.dumps(data.model_dump(by_alias=True), indent=2, default=str))
        return

    if html is not None:
        html_content = render_html(data)
        Path(html).write_text(html_content, encoding="utf-8")
        typer.echo(f"HTML report saved to {html}")
        return

    render_dashboard(data, top=top)
