"""CLI entry point — will be populated in Phase 8."""

import typer

app = typer.Typer(
    name="dotclaude",
    help="Analyze and visualize your Claude Code usage patterns",
    no_args_is_help=True,
)


@app.callback(invoke_without_command=True)
def main(version: bool = typer.Option(False, "--version", "-v", help="Show version")) -> None:
    """dotclaude — Claude Code Usage Analyzer."""
    if version:
        from dotclaude import __version__

        typer.echo(f"dotclaude {__version__}")
        raise typer.Exit()
