"""Pull command — fetch recommended or team-standard files from the server."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from dotclaude_types.models import PullItem, PullPackage
from rich.console import Console
from rich.table import Table

from dotclaude.utils.api_client import ApiError, AuthRequiredError, api_request
from dotclaude.utils.file_writer import safe_write

_console = Console()
pull_app = typer.Typer(name="pull", help="Pull recommended files from the dotclaude server")

_DEFAULT_BASE_DIR = Path("~/.claude")


async def _fetch_package(team_id: str | None) -> PullPackage:
    """GET /api/pull and parse the response into a PullPackage.

    Args:
        team_id: Optional team ID to pull team-standard files instead of
            personal recommendations.

    Returns:
        Parsed :class:`~dotclaude_types.models.PullPackage`.

    Raises:
        AuthRequiredError: If the user is not logged in.
        ApiError: If the server returns a non-success response.
    """
    path = "/api/pull"
    if team_id:
        path = f"{path}?team_id={team_id}"

    res = await api_request(path, method="GET")

    if not res.is_success:
        try:
            body = res.json()
            detail = body.get("detail", res.reason_phrase)
        except Exception:
            detail = res.reason_phrase
        raise ApiError(detail or "Pull failed", res.status_code)

    return PullPackage.model_validate(res.json())


def _apply_items(base_dir: Path, items: list[PullItem]) -> list[dict[str, str]]:
    """Write each PullItem to disk and collect result metadata.

    Items that would escape base_dir are skipped with a warning.

    Args:
        base_dir: Resolved base directory (e.g., ``~/.claude``).
        items: List of files to write.

    Returns:
        List of dicts with keys ``action``, ``type``, ``path``, and
        optionally ``backup`` (the backup suffix for updated files).
    """
    results: list[dict[str, str]] = []

    for item in items:
        try:
            action = safe_write(base_dir, item.target_path, item.content)
        except ValueError:
            _console.print(
                f"[yellow]\u26a0  Skipped (path traversal blocked): {item.target_path}[/yellow]"
            )
            continue

        entry: dict[str, str] = {
            "action": action,
            "type": item.type,
            "path": item.target_path,
        }
        if action == "updated":
            # Record the backup extension so it can be surfaced in output.
            resolved = (base_dir / item.target_path).resolve()
            # Find the most recently created .bak file for this path.
            parent = resolved.parent
            stem = resolved.stem
            suffix = resolved.suffix
            bak_pattern = f"{stem}{suffix}.bak.*"
            bak_files = sorted(parent.glob(bak_pattern))
            if bak_files:
                entry["backup"] = bak_files[-1].name
        results.append(entry)

    return results


def _print_apply_table(results: list[dict[str, str]]) -> None:
    """Print a Rich table summarising applied files.

    Args:
        results: Output of :func:`_apply_items`.
    """
    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("Action", style="green")
    table.add_column("Type")
    table.add_column("Path")

    for entry in results:
        path_cell = entry["path"]
        if "backup" in entry:
            path_cell = f"{path_cell} (backup: {entry['backup']})"
        table.add_row(entry["action"], entry["type"], path_cell)

    count = len(results)
    _console.print(f"\n[bold green]\u2714  Pull Complete ({count} file{'s' if count != 1 else ''})[/bold green]\n")
    _console.print(table)
    _console.print(
        "\n[dim]  chezmoi로 관리 중이라면 `dotclaude save-global`로 동기화하세요.[/dim]"
    )


def _print_dry_run_table(package: PullPackage) -> None:
    """Print a Rich preview table for --dry-run mode.

    Args:
        package: The :class:`~dotclaude_types.models.PullPackage` from the server.
    """
    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("Type")
    table.add_column("Path")
    table.add_column("Source")

    for item in package.items:
        table.add_row(item.type, item.target_path, item.source)

    count = len(package.items)
    _console.print(f"\n[bold]  Pull Preview ({count} file{'s' if count != 1 else ''})[/bold]\n")
    _console.print(table)
    _console.print("\n  Run without --dry-run to apply.")


async def _do_pull(
    team_id: str | None,
    dry_run: bool,
    base_dir: Path,
) -> None:
    """Core pull logic: fetch package from server and optionally apply files.

    Args:
        team_id: Optional team ID for team-standard files.
        dry_run: If True, only preview the changes without writing any files.
        base_dir: Base directory to write files into.

    Raises:
        AuthRequiredError: If the user is not logged in.
        ApiError: If the server returns a non-success response.
    """
    package = await _fetch_package(team_id)

    if not package.items:
        _console.print("[dim]  No files to pull.[/dim]")
        return

    if dry_run:
        _print_dry_run_table(package)
        return

    results = _apply_items(base_dir, package.items)
    _print_apply_table(results)


@pull_app.callback(invoke_without_command=True)
def pull(
    team: Annotated[
        str | None,
        typer.Option("--team", help="Pull team-standard files for the given team ID"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview files without writing to disk"),
    ] = False,
    path: Annotated[
        str | None,
        typer.Option("--path", help="Target directory (default: ~/.claude)"),
    ] = None,
) -> None:
    """Pull recommended or team-standard files from the dotclaude server."""

    base_dir = Path(path).expanduser().resolve() if path else _DEFAULT_BASE_DIR.expanduser().resolve()

    async def _run() -> None:
        try:
            await _do_pull(team_id=team, dry_run=dry_run, base_dir=base_dir)
        except AuthRequiredError as e:
            _console.print(f"[red]\u2716  로그인이 필요합니다: {e}[/red]")
            raise typer.Exit(1) from e
        except ApiError as e:
            _console.print(f"[red]\u2716  Pull failed: {e}[/red]")
            raise typer.Exit(1) from e
        except Exception as e:
            _console.print(f"[red]\u2716  Pull failed: {e}[/red]")
            raise typer.Exit(1) from e

    asyncio.run(_run())
