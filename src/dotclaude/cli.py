"""CLI entry point for dotclaude."""

from __future__ import annotations

from typing import Annotated

import typer

from dotclaude import __version__
from dotclaude.commands.config import config_app
from dotclaude.commands.login import login_app
from dotclaude.commands.register import register_app
from dotclaude.commands.serve import serve_app
from dotclaude.commands.sync import sync_app
from dotclaude.commands.team import team_app

app = typer.Typer(
    name="dotclaude",
    help="Analyze and visualize your Claude Code usage patterns",
    no_args_is_help=False,
    add_completion=False,
)

app.add_typer(config_app, name="config")
app.add_typer(login_app, name="login")
app.add_typer(register_app, name="register")
app.add_typer(sync_app, name="sync")
app.add_typer(serve_app, name="serve")
app.add_typer(team_app, name="team")


@app.command(name="format")
def format_cmd(
    path: Annotated[str, typer.Argument(help="Target ~/.claude directory")] = "~/.claude",
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview changes without writing files")] = False,
    force: Annotated[bool, typer.Option("--force", help="Overwrite existing dc_ fields")] = False,
    type_filter: Annotated[
        str | None,
        typer.Option("--type", help="Filter by type: rule | agent | skill | command"),
    ] = None,
) -> None:
    """Apply dc_ frontmatter to Markdown files in the target directory."""
    from dotclaude.commands.format import run_format

    run_format(path=path, dry_run=dry_run, force=force, type_filter=type_filter)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context = typer.Context,
    path: Annotated[str | None, typer.Option("--path", help="Custom path to ~/.claude directory")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output raw JSON instead of the dashboard")] = False,
    since: Annotated[str | None, typer.Option("--since", help="Include only records on or after this date (YYYY-MM-DD)")] = None,
    until: Annotated[str | None, typer.Option("--until", help="Include only records on or before this date (YYYY-MM-DD)")] = None,
    top: Annotated[int | None, typer.Option("--top", help="Max items per section")] = None,
    html: Annotated[str | None, typer.Option("--html", help="Export report as HTML file")] = None,
    insights: Annotated[bool, typer.Option("--insights", help="Analyze usage patterns with AI")] = False,
    evolve: Annotated[bool, typer.Option("--evolve", help="Suggest missing agents, rules, and hooks")] = False,
    version: Annotated[bool, typer.Option("--version", "-v", help="Show version")] = False,
) -> None:
    """dotclaude -- Claude Code Usage Analyzer."""
    if version:
        typer.echo(f"dotclaude {__version__}")
        raise typer.Exit()

    # If a subcommand was invoked, don't run the default action
    if ctx.invoked_subcommand is not None:
        return

    if evolve:
        from dotclaude.commands.insights import run_insights

        run_insights(path=path, evolve=True)
        return

    if insights:
        from dotclaude.commands.insights import run_insights

        run_insights(path=path, evolve=False)
        return

    # Default: run analyze
    from dotclaude.commands.analyze import run_analyze

    html_path = html if html is not None else None

    run_analyze(
        path=path,
        json_output=json_output,
        since=since,
        until=until,
        top=top,
        html=html_path,
    )
