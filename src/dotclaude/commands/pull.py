"""Pull command — fetch recommended or team-standard files from the server."""

from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path
from typing import Annotated, Any

import typer
from dotclaude_types.models import PullItem, PullPackage
from rich.console import Console
from rich.table import Table

from dotclaude.utils.api_client import ApiError, AuthRequiredError, api_request
from dotclaude.utils.file_writer import safe_write

_console = Console()
pull_app = typer.Typer(name="pull", help="Pull recommended files from the dotclaude server")

_DEFAULT_BASE_DIR = Path("~/.claude")


# ---------------------------------------------------------------------------
# Direct pull helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Workflow helpers
# ---------------------------------------------------------------------------


def _parse_workflow_items(output_data: dict[str, Any]) -> list[PullItem]:
    """Extract PullItem list from workflow output_data.

    Args:
        output_data: The ``output_data`` dict from a workflow run response.

    Returns:
        List of parsed :class:`~dotclaude_types.models.PullItem` objects.
        Returns an empty list when ``items`` key is absent or empty.
    """
    raw_items: list[Any] = output_data.get("items", [])
    result: list[PullItem] = []
    for raw in raw_items:
        # Skip items that cannot be parsed rather than aborting entirely.
        with contextlib.suppress(Exception):
            result.append(PullItem.model_validate(raw))
    return result


def _print_workflow_preview(items: list[PullItem], run_id: str) -> None:
    """Display a Rich table previewing workflow items.

    Args:
        items: Files the workflow recommends to apply.
        run_id: Workflow run ID (shown in the footer hint).
    """
    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("Type")
    table.add_column("Path")
    table.add_column("Source")

    for item in items:
        table.add_row(item.type, item.target_path, item.source)

    count = len(items)
    _console.print(
        f"\n[bold]  Workflow Preview ({count} file{'s' if count != 1 else ''})[/bold]"
        f"  [dim](run id: {run_id})[/dim]\n"
    )
    _console.print(table)


def _print_workflow_status(run_data: dict[str, Any]) -> None:
    """Print a workflow run's status and item preview.

    Args:
        run_data: Raw JSON dict from ``GET /api/workflows/{run_id}``.
    """
    run_id: str = run_data.get("id", "")
    status: str = run_data.get("status", "unknown")
    output_data: dict[str, Any] = run_data.get("output_data") or {}
    items = _parse_workflow_items(output_data)

    _console.print(f"\n[bold]Workflow[/bold] [cyan]{run_id}[/cyan]  status: [bold]{status}[/bold]")

    if items:
        _print_workflow_preview(items, run_id)
    else:
        _console.print("[dim]  No items in output_data.[/dim]")


async def _start_workflow(team_id: str | None) -> dict[str, Any]:
    """POST /api/workflows/recommend-apply to start a new workflow run.

    Args:
        team_id: Optional team ID to scope the recommendation.

    Returns:
        Raw JSON dict from the server (workflow run object).

    Raises:
        AuthRequiredError: If the user is not logged in.
        ApiError: If the server returns a non-success response.
    """
    body: dict[str, Any] = {"team_id": team_id}
    res = await api_request("/api/workflows/recommend-apply", method="POST", json_body=body)

    if not res.is_success:
        try:
            detail = res.json().get("detail", res.reason_phrase)
        except Exception:
            detail = res.reason_phrase
        raise ApiError(detail or "Workflow start failed", res.status_code)

    return res.json()  # type: ignore[no-any-return]


async def _get_workflow(run_id: str) -> dict[str, Any]:
    """GET /api/workflows/{run_id} to retrieve a workflow run.

    Args:
        run_id: The workflow run UUID.

    Returns:
        Raw JSON dict from the server.

    Raises:
        AuthRequiredError: If the user is not logged in.
        ApiError: If the server returns a non-success response.
    """
    res = await api_request(f"/api/workflows/{run_id}", method="GET")

    if not res.is_success:
        try:
            detail = res.json().get("detail", res.reason_phrase)
        except Exception:
            detail = res.reason_phrase
        raise ApiError(detail or "Workflow fetch failed", res.status_code)

    return res.json()  # type: ignore[no-any-return]


async def _approve_workflow(run_id: str) -> dict[str, Any]:
    """POST /api/workflows/{run_id}/approve.

    Args:
        run_id: The workflow run UUID.

    Returns:
        Raw JSON dict from the server.

    Raises:
        AuthRequiredError: If the user is not logged in.
        ApiError: If the server returns a non-success response.
    """
    res = await api_request(f"/api/workflows/{run_id}/approve", method="POST")

    if not res.is_success:
        try:
            detail = res.json().get("detail", res.reason_phrase)
        except Exception:
            detail = res.reason_phrase
        raise ApiError(detail or "Workflow approval failed", res.status_code)

    return res.json()  # type: ignore[no-any-return]


async def _reject_workflow(run_id: str) -> None:
    """POST /api/workflows/{run_id}/reject.

    Args:
        run_id: The workflow run UUID.

    Raises:
        AuthRequiredError: If the user is not logged in.
        ApiError: If the server returns a non-success response.
    """
    res = await api_request(f"/api/workflows/{run_id}/reject", method="POST")

    if not res.is_success:
        try:
            detail = res.json().get("detail", res.reason_phrase)
        except Exception:
            detail = res.reason_phrase
        raise ApiError(detail or "Workflow rejection failed", res.status_code)


async def _do_workflow(team_id: str | None, base_dir: Path) -> None:
    """Start a workflow, show preview, and prompt for approval.

    If the user confirms, the workflow is approved and files are applied
    immediately.  If the user declines, the workflow is rejected.

    Args:
        team_id: Optional team ID to scope the recommendation.
        base_dir: Base directory to write files into on approval.

    Raises:
        AuthRequiredError: If the user is not logged in.
        ApiError: If any API call fails.
    """
    _console.print("[dim]  Starting workflow...[/dim]")
    run_data = await _start_workflow(team_id)

    run_id: str = run_data.get("id", "")
    output_data: dict[str, Any] = run_data.get("output_data") or {}
    items = _parse_workflow_items(output_data)

    if not items:
        _console.print("[dim]  No files recommended.[/dim]")
        return

    _print_workflow_preview(items, run_id)

    confirmed = typer.confirm("\nApply these files?", default=False)

    if confirmed:
        await _approve_workflow(run_id)
        # Re-fetch to get the latest output_data after approval.
        approved_data = await _get_workflow(run_id)
        approved_output: dict[str, Any] = approved_data.get("output_data") or {}
        approved_items = _parse_workflow_items(approved_output)
        # Fall back to items from the initial response if re-fetch is empty.
        apply_items = approved_items if approved_items else items
        results = _apply_items(base_dir, apply_items)
        _print_apply_table(results)
    else:
        await _reject_workflow(run_id)
        _console.print("[dim]  Cancelled.[/dim]")


async def _do_approve(run_id: str, base_dir: Path) -> None:
    """Approve a workflow run and apply its files.

    Args:
        run_id: The workflow run UUID to approve.
        base_dir: Base directory to write files into.

    Raises:
        AuthRequiredError: If the user is not logged in.
        ApiError: If any API call fails.
    """
    await _approve_workflow(run_id)
    run_data = await _get_workflow(run_id)
    output_data: dict[str, Any] = run_data.get("output_data") or {}
    items = _parse_workflow_items(output_data)

    if not items:
        _console.print("[dim]  Workflow approved but no files to apply.[/dim]")
        return

    results = _apply_items(base_dir, items)
    _print_apply_table(results)


async def _do_reject(run_id: str) -> None:
    """Reject a workflow run.

    Args:
        run_id: The workflow run UUID to reject.

    Raises:
        AuthRequiredError: If the user is not logged in.
        ApiError: If the API call fails.
    """
    await _reject_workflow(run_id)
    _console.print("[green]\u2714[/green]  Workflow rejected.")


async def _do_status(run_id: str) -> None:
    """Fetch and display the status of a workflow run.

    Args:
        run_id: The workflow run UUID.

    Raises:
        AuthRequiredError: If the user is not logged in.
        ApiError: If the API call fails.
    """
    run_data = await _get_workflow(run_id)
    _print_workflow_status(run_data)


# ---------------------------------------------------------------------------
# CLI command
# ---------------------------------------------------------------------------


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
    workflow: Annotated[
        bool,
        typer.Option("--workflow", help="Start a workflow run with approval step"),
    ] = False,
    approve: Annotated[
        str | None,
        typer.Option("--approve", help="Approve a workflow run by ID and apply its files"),
    ] = None,
    reject: Annotated[
        str | None,
        typer.Option("--reject", help="Reject a workflow run by ID"),
    ] = None,
    status: Annotated[
        str | None,
        typer.Option("--status", help="Show the status of a workflow run by ID"),
    ] = None,
) -> None:
    """Pull recommended or team-standard files from the dotclaude server.

    Direct pull (immediate apply):

        dotclaude pull [--team ID] [--dry-run] [--path DIR]

    Workflow pull (preview + approval):

        dotclaude pull --workflow [--team ID]
        dotclaude pull --approve <run-id>
        dotclaude pull --reject <run-id>
        dotclaude pull --status <run-id>
    """
    base_dir = (
        Path(path).expanduser().resolve() if path else _DEFAULT_BASE_DIR.expanduser().resolve()
    )

    async def _run() -> None:
        try:
            if status is not None:
                await _do_status(status)
            elif reject is not None:
                await _do_reject(reject)
            elif approve is not None:
                await _do_approve(approve, base_dir)
            elif workflow:
                await _do_workflow(team_id=team, base_dir=base_dir)
            else:
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
