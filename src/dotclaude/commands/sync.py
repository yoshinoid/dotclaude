"""Sync command — parse ~/.claude and push to the dotclaude server."""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import Any

import typer
from dotclaude_types.models import KnowledgeItem
from rich.console import Console

from dotclaude import __version__ as package_version
from dotclaude.commands.format import TYPE_GLOBS
from dotclaude.parser import analyze
from dotclaude.utils.api_client import ApiError, AuthRequiredError, api_request

_console = Console()
sync_app = typer.Typer(name="sync", help="Sync ~/.claude usage data to the dotclaude server")


def _collect_knowledge_items(claude_dir: str) -> list[KnowledgeItem]:
    """Collect ~/.claude/ config files and convert to KnowledgeItem models.

    For each Markdown file found under *claude_dir* (agents, rules, skills,
    commands), reads its content and builds a :class:`~dotclaude_types.models.KnowledgeItem`
    suitable for ``POST /api/knowledge/bulk``.

    dc_-prefixed frontmatter fields are used when present; otherwise
    :func:`~dotclaude_rag.frontmatter.inference.infer_frontmatter` derives them
    automatically from the file path and content.

    Args:
        claude_dir: Absolute path to the ``~/.claude`` directory.

    Returns:
        List of :class:`~dotclaude_types.models.KnowledgeItem` instances,
        one per collected file.
    """
    from dotclaude_rag.frontmatter.inference import infer_frontmatter
    from dotclaude_rag.frontmatter.parser import extract_dc_fields, parse

    base = Path(claude_dir).expanduser().resolve()
    items: list[KnowledgeItem] = []

    for _file_type, glob_pattern in TYPE_GLOBS:
        for file_path in sorted(base.glob(glob_pattern)):
            if not file_path.is_file():
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
            except OSError:
                continue

            # Compute source_path relative to the claude dir.
            try:
                relative = file_path.relative_to(base)
                source_path = relative.as_posix()
            except ValueError:
                source_path = file_path.name

            # Parse frontmatter; use dc_ fields when available, otherwise infer.
            metadata, _body = parse(content)
            fm = extract_dc_fields(metadata)
            if fm is None:
                fm = infer_frontmatter(str(file_path), content)

            content_hash = hashlib.sha256(content.encode()).hexdigest()

            items.append(
                KnowledgeItem(
                    type=fm.dc_type,
                    stack=fm.dc_stack,
                    scope=fm.dc_scope,
                    title=fm.dc_description or source_path,
                    description=fm.dc_description,
                    content=content,
                    content_hash=content_hash,
                    source_path=source_path,
                )
            )

    return items


async def _upload_knowledge(items: list[KnowledgeItem]) -> dict[str, Any]:
    """POST /api/knowledge/bulk with the collected items.

    Args:
        items: List of :class:`~dotclaude_types.models.KnowledgeItem` instances
            produced by :func:`_collect_knowledge_items`.

    Returns:
        Parsed JSON response dict from the server
        (``uploaded``, ``skipped``, ``chunks_created``).

    Raises:
        ApiError: When the server returns a non-success response.
        AuthRequiredError: When the user is not logged in.
    """
    res = await api_request(
        "/api/knowledge/bulk",
        method="POST",
        json_body={"items": [item.model_dump(by_alias=True) for item in items]},
    )

    if not res.is_success:
        try:
            body = res.json()
            detail = body.get("detail", res.reason_phrase)
        except Exception:
            detail = res.reason_phrase
        raise ApiError(detail or "Knowledge upload failed", res.status_code)

    return dict(res.json())


async def _do_sync(claude_dir: str | None = None) -> None:
    """Perform a single sync operation.

    Step 1: Analyze the Claude directory and POST snapshot to /api/sync.
    Step 2: Collect knowledge files and POST to /api/knowledge/bulk.
            Failure at step 2 emits a warning but does not abort the command.
    """
    resolved_dir = claude_dir or str(Path("~/.claude").expanduser())

    # --- Step 1: snapshot sync ---
    try:
        data = await analyze(claude_dir)
    except Exception as e:
        raise RuntimeError(f"Failed to analyze Claude directory: {e}") from e

    res = await api_request(
        "/api/sync",
        method="POST",
        json_body={"data": data.model_dump(by_alias=True), "client_version": package_version},
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

    # --- Step 2: knowledge upload ---
    try:
        items = _collect_knowledge_items(resolved_dir)
    except Exception as e:
        _console.print(f"[yellow]\u26a0[/yellow]  Knowledge collection failed: {e}")
        return

    if not items:
        return

    try:
        upload_result = await _upload_knowledge(items)
        uploaded = upload_result.get("uploaded", 0)
        skipped = upload_result.get("skipped", 0)
        chunks = upload_result.get("chunks_created", 0)
        _console.print(
            f"  [dim]Knowledge: {len(items)} files \u2192 "
            f"{uploaded} uploaded, {skipped} unchanged, {chunks} chunks created[/dim]"
        )
    except AuthRequiredError as e:
        _console.print(f"[yellow]\u26a0  Knowledge upload failed: {e}[/yellow]")
    except ApiError as e:
        _console.print(
            f"[yellow]\u26a0  Knowledge upload failed: {e.status_code} {e}[/yellow]"
        )
    except Exception as e:
        _console.print(f"[yellow]\u26a0  Knowledge upload failed: {e}[/yellow]")


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
