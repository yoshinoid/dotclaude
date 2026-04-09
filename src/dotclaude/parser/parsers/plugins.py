"""Plugins parser, ported from TypeScript parsers/plugins.ts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dotclaude_types.models import PluginsStatus
from dotclaude.parser.utils import safe_json_parse


def _is_record(value: Any) -> bool:
    return isinstance(value, dict)


def parse_plugins(plugins_dir: str) -> PluginsStatus:
    """Parse the plugins directory to extract marketplace and blocklist information."""
    base = Path(plugins_dir)

    # known_marketplaces.json
    marketplace_names: list[str] = []
    marketplaces_file = base / "known_marketplaces.json"
    try:
        raw = marketplaces_file.read_text(encoding="utf-8")
        parsed = safe_json_parse(raw)
        if _is_record(parsed):
            assert isinstance(parsed, dict)
            marketplace_names = [
                key for key, value in parsed.items() if _is_record(value)
            ]
    except OSError:
        pass  # File may not exist — that is fine

    # blocklist.json
    blocked_count = 0
    blocklist_file = base / "blocklist.json"
    try:
        raw = blocklist_file.read_text(encoding="utf-8")
        parsed = safe_json_parse(raw)
        if _is_record(parsed):
            assert isinstance(parsed, dict)
            plugins = parsed.get("plugins")
            if isinstance(plugins, list):
                blocked_count = len(plugins)
    except OSError:
        pass  # File may not exist — that is fine

    return PluginsStatus(
        marketplace_count=len(marketplace_names),
        marketplaces=sorted(marketplace_names),
        blocked_count=blocked_count,
    )
