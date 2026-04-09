"""Directory scanner for ~/.claude, ported from TypeScript scanner.ts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# Directories and files that should be ignored during scanning.
_IGNORE_NAMES: frozenset[str] = frozenset(
    [
        ".credentials.json",
        "cache",
        "backups",
        "downloads",
        "file-history",
        "ide",
        "shell-snapshots",
        "session-env",
    ]
)


@dataclass
class ScanManifest:
    """Result of scanning the ~/.claude directory."""

    claude_dir: str
    settings_file: str | None = None
    history_file: str | None = None
    session_files: list[str] = field(default_factory=list)
    project_dirs: list[str] = field(default_factory=list)
    agent_files: list[str] = field(default_factory=list)
    command_files: list[str] = field(default_factory=list)
    hook_dir: str | None = None
    rule_dirs: list[str] = field(default_factory=list)
    skill_dirs: list[str] = field(default_factory=list)
    plugins_dir: str | None = None


def _safe_iterdir(directory: Path) -> list[Path]:
    """Safely list directory contents; returns empty list on any error."""
    try:
        return list(directory.iterdir())
    except OSError:
        return []


def _collect_md_files(directory: Path) -> list[str]:
    """Recursively collect all *.md file paths under a directory."""
    results: list[str] = []
    try:
        entries = list(directory.iterdir())
    except OSError:
        return results

    for entry in entries:
        if entry.name in _IGNORE_NAMES:
            continue
        if entry.is_dir():
            results.extend(_collect_md_files(entry))
        elif entry.is_file() and entry.suffix == ".md":
            results.append(str(entry))

    return results


def scan_claude_dir(claude_dir: str) -> ScanManifest:
    """Scan the ~/.claude directory and return a manifest of discovered files.

    Groups discovered files by category. Never raises — missing directories
    yield empty arrays.
    """
    base = Path(claude_dir)
    manifest = ScanManifest(claude_dir=claude_dir)

    # settings.json
    settings_path = base / "settings.json"
    if settings_path.is_file():
        manifest.settings_file = str(settings_path)

    # history.jsonl
    history_path = base / "history.jsonl"
    if history_path.is_file():
        manifest.history_file = str(history_path)

    # sessions/*.json
    sessions_dir = base / "sessions"
    if sessions_dir.is_dir():
        for entry in _safe_iterdir(sessions_dir):
            if entry.name in _IGNORE_NAMES:
                continue
            if entry.suffix == ".json" and entry.is_file():
                manifest.session_files.append(str(entry))

    # projects/<encoded>/
    projects_dir = base / "projects"
    if projects_dir.is_dir():
        for entry in _safe_iterdir(projects_dir):
            if entry.name in _IGNORE_NAMES:
                continue
            if entry.is_dir():
                manifest.project_dirs.append(str(entry))

    # agents/*.md
    agents_dir = base / "agents"
    if agents_dir.is_dir():
        for entry in _safe_iterdir(agents_dir):
            if entry.name in _IGNORE_NAMES:
                continue
            if entry.suffix == ".md" and entry.is_file():
                manifest.agent_files.append(str(entry))

    # commands/*.md
    commands_dir = base / "commands"
    if commands_dir.is_dir():
        for entry in _safe_iterdir(commands_dir):
            if entry.name in _IGNORE_NAMES:
                continue
            if entry.suffix == ".md" and entry.is_file():
                manifest.command_files.append(str(entry))

    # hooks/
    hooks_dir = base / "hooks"
    if hooks_dir.is_dir():
        manifest.hook_dir = str(hooks_dir)

    # rules/**/*.md
    rules_dir = base / "rules"
    if rules_dir.is_dir():
        manifest.rule_dirs = _collect_md_files(rules_dir)

    # skills/*/
    skills_dir = base / "skills"
    if skills_dir.is_dir():
        for entry in _safe_iterdir(skills_dir):
            if entry.name in _IGNORE_NAMES:
                continue
            if entry.is_dir():
                manifest.skill_dirs.append(str(entry))

    # plugins/
    plugins_dir = base / "plugins"
    if plugins_dir.is_dir():
        manifest.plugins_dir = str(plugins_dir)

    return manifest
