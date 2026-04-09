"""Format command — apply dc_ frontmatter to ~/.claude Markdown files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import typer
from dotclaude_rag.frontmatter.writer import FormatResult, format_file
from rich.console import Console
from rich.table import Table

_console = Console()

# Ordered type labels matching the collection order.
_FILE_TYPE = Literal["agent", "rule", "skill", "command"]

TYPE_GLOBS: list[tuple[_FILE_TYPE, str]] = [
    ("agent", "agents/*.md"),
    ("rule", "rules/**/*.md"),
    ("skill", "skills/*/SKILL.md"),
    ("command", "commands/*.md"),
]


@dataclass
class _TypeSummary:
    file_type: str
    total: int = 0
    added: int = 0
    updated: int = 0
    skipped: int = 0


@dataclass
class _FormatSummary:
    by_type: list[_TypeSummary] = field(default_factory=list)

    @property
    def total_files(self) -> int:
        return sum(t.total for t in self.by_type)

    @property
    def total_added(self) -> int:
        return sum(t.added for t in self.by_type)

    @property
    def total_updated(self) -> int:
        return sum(t.updated for t in self.by_type)

    @property
    def total_skipped(self) -> int:
        return sum(t.skipped for t in self.by_type)


def _collect_files(
    base: Path,
    type_filter: str | None,
) -> list[tuple[_FILE_TYPE, Path]]:
    """Collect Markdown files matching the known patterns under *base*.

    Args:
        base: Expanded base directory (e.g. ``~/.claude``).
        type_filter: When set, only files of this type are collected.

    Returns:
        Ordered list of ``(file_type, path)`` pairs.
    """
    collected: list[tuple[_FILE_TYPE, Path]] = []
    for file_type, glob_pattern in TYPE_GLOBS:
        if type_filter is not None and file_type != type_filter:
            continue
        for path in sorted(base.glob(glob_pattern)):
            if path.is_file():
                collected.append((file_type, path))
    return collected


def _render_dry_run_table(summary: _FormatSummary) -> None:
    """Print a Rich table showing the dry-run preview."""
    _console.print()
    _console.print(
        f"  [bold]Format Preview[/bold] ({summary.total_files} files)"
    )
    _console.print()

    table = Table(
        show_header=True,
        header_style="bold",
        box=None,
        padding=(0, 2),
    )
    table.add_column("Type", style="cyan")
    table.add_column("Files", justify="right")
    table.add_column("To add", justify="right")
    table.add_column("To update", justify="right")
    table.add_column("Skipped", justify="right")

    for ts in summary.by_type:
        table.add_row(
            ts.file_type,
            str(ts.total),
            str(ts.added),
            str(ts.updated),
            str(ts.skipped),
        )

    _console.print(table)
    _console.print()
    _console.print("  Run without [bold]--dry-run[/bold] to apply changes.")
    _console.print()


def _render_complete_table(summary: _FormatSummary) -> None:
    """Print a Rich table showing the applied changes."""
    _console.print()
    _console.print(
        f"  [bold green]\u2714[/bold green]  [bold]Format Complete[/bold]"
        f"  ({summary.total_files} files processed)"
    )
    _console.print()

    table = Table(
        show_header=True,
        header_style="bold",
        box=None,
        padding=(0, 2),
    )
    table.add_column("Type", style="cyan")
    table.add_column("Files", justify="right")
    table.add_column("Added", justify="right", style="green")
    table.add_column("Updated", justify="right", style="yellow")
    table.add_column("Skipped", justify="right", style="dim")

    for ts in summary.by_type:
        table.add_row(
            ts.file_type,
            str(ts.total),
            str(ts.added),
            str(ts.updated),
            str(ts.skipped),
        )

    _console.print(table)
    _console.print()

    if summary.total_added > 0 or summary.total_updated > 0:
        _console.print(
            "  [dim]chezmoi로 관리 중이라면 "
            "`dotclaude save-global`로 동기화하세요.[/dim]"
        )
        _console.print()


def run_format(
    path: str = "~/.claude",
    *,
    dry_run: bool = False,
    force: bool = False,
    type_filter: str | None = None,
) -> None:
    """Apply dc_ frontmatter to Markdown files under *path*.

    Collects all agent, rule, skill, and command Markdown files found in the
    target directory, calls :func:`~dotclaude_rag.frontmatter.writer.format_file`
    on each, and renders a Rich summary table.

    Args:
        path: Root directory to scan (``~`` is expanded).  Defaults to
            ``~/.claude``.
        dry_run: When ``True`` files are never written; only a preview is shown.
        force: Overwrite existing ``dc_`` fields even when already present.
        type_filter: Restrict processing to a single file type
            (``"rule"``, ``"agent"``, ``"skill"``, or ``"command"``).
    """
    base = Path(path).expanduser().resolve()

    if not base.exists():
        _console.print(f"[red]Error:[/red] Directory not found: {base}")
        raise typer.Exit(1)

    valid_types = {"rule", "agent", "skill", "command"}
    if type_filter is not None and type_filter not in valid_types:
        _console.print(
            f"[red]Error:[/red] Unknown type '{type_filter}'. "
            f"Choose from: {', '.join(sorted(valid_types))}"
        )
        raise typer.Exit(1)

    files = _collect_files(base, type_filter)

    # Build per-type summary buckets.
    type_order: list[_FILE_TYPE] = ["agent", "rule", "skill", "command"]
    buckets: dict[str, _TypeSummary] = {t: _TypeSummary(file_type=t) for t in type_order}

    if not files:
        _console.print(
            f"\n  [dim]No matching Markdown files found under {base}[/dim]\n"
        )
        return

    for file_type, file_path in files:
        bucket = buckets[file_type]
        bucket.total += 1

        try:
            result: FormatResult = format_file(
                str(file_path),
                force=force,
                dry_run=dry_run,
            )
        except Exception as exc:  # noqa: BLE001
            _console.print(
                f"[yellow]\u26a0[/yellow]  Skipped {file_path.name}: {exc}"
            )
            bucket.skipped += 1
            continue

        if result.action == "added":
            bucket.added += 1
        elif result.action == "updated":
            bucket.updated += 1
        else:
            bucket.skipped += 1

    summary = _FormatSummary(by_type=list(buckets.values()))

    if dry_run:
        _render_dry_run_table(summary)
    else:
        _render_complete_table(summary)
