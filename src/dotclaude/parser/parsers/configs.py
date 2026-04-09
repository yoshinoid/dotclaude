"""Configs parser, ported from TypeScript parsers/configs.ts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotclaude_types.models import (
    AgentsStatus,
    CommandsStatus,
    HooksStatus,
    McpServersStatus,
    RulesStatus,
    SkillsStatus,
)
from dotclaude.parser.parsers.settings import RawHookDefinition, parse_settings


def _safe_iterdir(directory: Path) -> list[Path]:
    try:
        return list(directory.iterdir())
    except OSError:
        return []


def _extract_rule_domains(rules_dir: str, rule_files: list[str]) -> list[str]:
    """Extract top-level domain names from rules directory file paths.

    Domain = first subdirectory under rules/.
    Example: rules/frontend/typescript.md → "frontend"
    """
    if not rules_dir:
        return []

    base = Path(rules_dir)
    domains: set[str] = set()

    for file_path in rule_files:
        try:
            rel = Path(file_path).relative_to(base)
        except ValueError:
            continue
        parts = rel.parts
        if len(parts) >= 2:
            # Has a subdirectory — the subdirectory is the domain
            domain = parts[0]
            if domain:
                domains.add(domain)
        # Files directly in rules/ are not added (no domain)

    return sorted(domains)


def _parse_hooks_dir(hook_dir: str, settings_hooks: HooksStatus) -> HooksStatus:
    """Parse the hooks directory structure.

    Uses settings_hooks as primary source and augments with hookDir scripts.
    """
    by_event: dict[str, int] = dict(settings_hooks.by_event)
    total_hooks = settings_hooks.total_hooks

    hook_path = Path(hook_dir)
    for entry in _safe_iterdir(hook_path):
        if not entry.is_dir():
            continue
        event_name = entry.name
        scripts = [e for e in _safe_iterdir(entry) if e.is_file()]
        if scripts and event_name not in by_event:
            # Only add if not already counted via settings.json
            by_event[event_name] = len(scripts)
            total_hooks += len(scripts)

    return HooksStatus(total_hooks=total_hooks, by_event=by_event)


@dataclass
class ConfigsParseInput:
    """Input data for parse_configs."""

    agent_files: list[str]
    command_files: list[str]
    hook_dir: str | None
    rule_dirs: list[str]
    skill_dirs: list[str]
    settings_file: str | None


@dataclass
class ConfigsParseResult:
    """Result of parsing all config directories."""

    agents: AgentsStatus
    commands: CommandsStatus
    hooks: HooksStatus
    rules: RulesStatus
    skills: SkillsStatus
    mcp_servers: McpServersStatus
    hook_definitions: list[RawHookDefinition] = field(default_factory=list)


def _find_rules_root(rule_dirs: list[str]) -> str:
    """Walk up from first rule file to find the 'rules' directory."""
    if not rule_dirs:
        return ""

    current = Path(rule_dirs[0]).parent
    while current != current.parent:
        if current.name == "rules":
            return str(current)
        current = current.parent
    return ""


def parse_configs(input_data: ConfigsParseInput) -> ConfigsParseResult:
    """Enumerate config directories and extract metadata about agents, commands,
    hooks, rules, skills, MCP servers, and plugins.
    """
    # Agents
    agent_names = [Path(f).stem for f in input_data.agent_files]

    # Commands
    command_names = [Path(f).stem for f in input_data.command_files]

    # Rules
    rules_dir_root = _find_rules_root(input_data.rule_dirs)
    rule_domains = _extract_rule_domains(rules_dir_root, input_data.rule_dirs)

    # Collect relative file paths for rule files
    if rules_dir_root:
        base = Path(rules_dir_root)
        rule_files = sorted(
            str(Path(f).relative_to(base)).replace("\\", "/")
            for f in input_data.rule_dirs
        )
    else:
        rule_files = sorted(Path(f).name for f in input_data.rule_dirs)

    # Skills
    skill_names = [Path(d).name for d in input_data.skill_dirs]

    # Hooks — start from settings.json hooks, augment with hookDir
    settings_hooks = HooksStatus(total_hooks=0, by_event={})
    mcp_servers_raw: dict[str, Any] = {"count": 0, "names": []}
    hook_definitions: list[RawHookDefinition] = []

    if input_data.settings_file is not None:
        settings_result = parse_settings(input_data.settings_file)
        settings_hooks = settings_result.hooks
        mcp_servers_raw = settings_result.mcp_servers
        hook_definitions = settings_result.hook_definitions

    hooks_status = settings_hooks
    if input_data.hook_dir is not None and Path(input_data.hook_dir).is_dir():
        hooks_status = _parse_hooks_dir(input_data.hook_dir, settings_hooks)

    mcp_count: int = mcp_servers_raw.get("count", 0)
    mcp_names: list[str] = mcp_servers_raw.get("names", [])

    return ConfigsParseResult(
        agents=AgentsStatus(count=len(agent_names), names=sorted(agent_names)),
        commands=CommandsStatus(count=len(command_names), names=sorted(command_names)),
        hooks=hooks_status,
        rules=RulesStatus(
            count=len(input_data.rule_dirs),
            domains=rule_domains,
            files=rule_files,
        ),
        skills=SkillsStatus(count=len(skill_names), names=sorted(skill_names)),
        mcp_servers=McpServersStatus(count=mcp_count, names=mcp_names),
        hook_definitions=hook_definitions,
    )
