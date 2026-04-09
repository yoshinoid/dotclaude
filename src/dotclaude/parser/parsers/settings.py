"""Settings parser, ported from TypeScript parsers/settings.ts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotclaude_types.models import HooksStatus
from dotclaude.parser.utils import safe_json_parse


@dataclass
class RawHookDefinition:
    """A single hook definition extracted from settings.json."""

    event: str
    matcher: str
    command: str


@dataclass
class SettingsParseResult:
    """Result of parsing settings.json."""

    hooks: HooksStatus
    hook_definitions: list[RawHookDefinition] = field(default_factory=list)
    mcp_servers: dict[str, Any] = field(default_factory=dict)
    permission_count: int = 0


def _is_record(value: Any) -> bool:
    """Return True if value is a dict-like object."""
    return isinstance(value, dict)


def parse_settings(settings_file: str) -> SettingsParseResult:
    """Parse settings.json and extract hooks config, MCP servers, and permissions.

    Returns a safe default result on any read/parse error.
    """
    default_result = SettingsParseResult(
        hooks=HooksStatus(total_hooks=0, by_event={}),
        hook_definitions=[],
        mcp_servers={"count": 0, "names": []},
        permission_count=0,
    )

    try:
        raw = Path(settings_file).read_text(encoding="utf-8")
    except OSError:
        return default_result

    parsed = safe_json_parse(raw)
    if not _is_record(parsed):
        return default_result

    assert isinstance(parsed, dict)

    # --- MCP servers ---
    mcp_servers_raw = parsed.get("mcpServers")
    mcp_names: list[str] = []
    if _is_record(mcp_servers_raw):
        assert isinstance(mcp_servers_raw, dict)
        mcp_names = list(mcp_servers_raw.keys())

    # --- Hooks ---
    by_event: dict[str, int] = {}
    total_hooks = 0
    hook_definitions: list[RawHookDefinition] = []

    hooks_raw = parsed.get("hooks")
    if _is_record(hooks_raw):
        assert isinstance(hooks_raw, dict)
        for event_name, event_hooks in hooks_raw.items():
            if not isinstance(event_hooks, list):
                continue
            count = len(event_hooks)
            if count > 0:
                by_event[event_name] = count
                total_hooks += count

            # Extract individual hook definitions for frequency estimation
            for hook_group in event_hooks:
                if not _is_record(hook_group):
                    continue
                assert isinstance(hook_group, dict)
                matcher = hook_group.get("matcher", "")
                if not isinstance(matcher, str):
                    matcher = ""
                inner_hooks = hook_group.get("hooks")
                if not isinstance(inner_hooks, list):
                    continue
                for hook in inner_hooks:
                    if not _is_record(hook):
                        continue
                    assert isinstance(hook, dict)
                    command = hook.get("command", "")
                    if isinstance(command, str) and command:
                        hook_definitions.append(
                            RawHookDefinition(
                                event=event_name,
                                matcher=matcher,
                                command=command,
                            )
                        )

    # --- Permissions ---
    permission_count = 0
    permissions_raw = parsed.get("permissions")
    if _is_record(permissions_raw):
        assert isinstance(permissions_raw, dict)
        allowed = permissions_raw.get("allow")
        denied = permissions_raw.get("deny")
        if isinstance(allowed, list) and all(isinstance(v, str) for v in allowed):
            permission_count += len(allowed)
        if isinstance(denied, list) and all(isinstance(v, str) for v in denied):
            permission_count += len(denied)

    return SettingsParseResult(
        hooks=HooksStatus(total_hooks=total_hooks, by_event=by_event),
        hook_definitions=hook_definitions,
        mcp_servers={"count": len(mcp_names), "names": mcp_names},
        permission_count=permission_count,
    )
