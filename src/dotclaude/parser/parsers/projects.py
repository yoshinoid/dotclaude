"""Projects parser, ported from TypeScript parsers/projects.ts."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotclaude.models import ProjectConfig, ProjectStats
from dotclaude.parser.utils import decode_project_path

_MEMORY_FILE_EXTENSIONS: frozenset[str] = frozenset([".md", ".txt", ".json"])

# Names of subdirectories within a project dir that are not session files.
_NON_SESSION_DIRS: frozenset[str] = frozenset(["subagents"])

# Marker files that indicate a project's tech stack.
_MANIFEST_FILES: dict[str, list[str]] = {
    "package.json": ["node"],
    "pyproject.toml": ["python"],
    "requirements.txt": ["python"],
    "go.mod": ["go"],
    "Cargo.toml": ["rust"],
    "pubspec.yaml": ["dart"],
    "build.gradle.kts": ["kotlin"],
    "build.gradle": ["java"],
    "pom.xml": ["java"],
    "Package.swift": ["swift"],
}

# Keywords to detect in CLAUDE.md content — maps keyword to tech/domain hint.
_CLAUDE_MD_KEYWORDS: dict[str, str] = {
    "python": "python",
    "fastapi": "fastapi",
    "django": "django",
    "flask": "flask",
    "typescript": "typescript",
    "react": "react",
    "next.js": "nextjs",
    "nextjs": "nextjs",
    "vue": "vue",
    "nuxt": "nuxt",
    "angular": "angular",
    "golang": "go",
    "go ": "go",
    "java": "java",
    "spring boot": "spring",
    "kotlin": "kotlin",
    "swift": "swift",
    "swiftui": "swiftui",
    "flutter": "flutter",
    "dart": "dart",
    "rust": "rust",
    "docker": "docker",
    "kubernetes": "k8s",
    "postgresql": "postgres",
    "postgres": "postgres",
    "mysql": "mysql",
}


def _safe_iterdir(directory: Path) -> list[Path]:
    try:
        return list(directory.iterdir())
    except OSError:
        return []


def _count_memory_files(directory: Path) -> int:
    """Count files with memory-like extensions in a directory (non-recursive)."""
    count = 0
    for entry in _safe_iterdir(directory):
        if entry.is_file() and entry.suffix in _MEMORY_FILE_EXTENSIONS:
            count += 1
    return count


def _get_last_modified(directory: Path) -> str:
    """Get the most recent mtime across all .jsonl files in a directory tree."""
    latest: float = 0.0

    def walk(d: Path) -> None:
        nonlocal latest
        for entry in _safe_iterdir(d):
            if entry.is_dir() and entry.name not in _NON_SESSION_DIRS:
                walk(entry)
            elif entry.is_file() and entry.suffix == ".jsonl":
                try:
                    mtime = entry.stat().st_mtime
                    if mtime > latest:
                        latest = mtime
                except OSError:
                    pass

    walk(directory)
    if latest > 0:
        return datetime.fromtimestamp(latest, tz=timezone.utc).isoformat()
    return datetime.fromtimestamp(0, tz=timezone.utc).isoformat()


def _count_jsonl_files(directory: Path) -> int:
    """Count the number of .jsonl session files in a project directory."""
    return sum(
        1 for entry in _safe_iterdir(directory) if entry.is_file() and entry.suffix == ".jsonl"
    )


def _scan_manifests(project_path: Path) -> list[str]:
    """Scan a project directory for manifest files and return detected tech stacks."""
    stacks: set[str] = set()
    for filename, techs in _MANIFEST_FILES.items():
        try:
            if (project_path / filename).exists():
                stacks.update(techs)
        except OSError:
            pass
    return sorted(stacks)


def _safe_read_file(file_path: Path, max_bytes: int = 8192) -> str:
    """Read a file's content safely, returning empty string on any error."""
    try:
        with file_path.open("rb") as f:
            data = f.read(max_bytes)
        return data.decode("utf-8", errors="replace")
    except OSError:
        return ""


def _scan_project_config(project_path: Path) -> ProjectConfig | None:
    """Scan a project's .claude/ directory and root for config presence.

    Returns None if the project path doesn't exist on disk.
    """
    try:
        if not project_path.exists():
            return None
    except OSError:
        return None

    claude_dir = project_path / ".claude"
    try:
        has_claude_dir = claude_dir.is_dir()
    except OSError:
        has_claude_dir = False

    # Check for CLAUDE.md in multiple locations
    claude_md_paths = [
        project_path / "CLAUDE.md",
        claude_dir / "CLAUDE.md",
    ]
    has_claude_md = False
    for p in claude_md_paths:
        try:
            if p.is_file():
                has_claude_md = True
                break
        except OSError:
            pass

    # Scan project agents
    agents: list[str] = []
    if has_claude_dir:
        agents_dir = claude_dir / "agents"
        for entry in _safe_iterdir(agents_dir):
            if entry.is_file() and entry.suffix == ".md":
                agents.append(entry.stem)

    # Scan project rules
    rules: list[str] = []
    if has_claude_dir:
        rules_dir = claude_dir / "rules"
        try:
            if rules_dir.is_dir():
                def collect_rules(d: Path, prefix: str) -> None:
                    for entry in _safe_iterdir(d):
                        if entry.is_dir():
                            new_prefix = f"{prefix}/{entry.name}" if prefix else entry.name
                            collect_rules(entry, new_prefix)
                        elif entry.is_file() and entry.suffix == ".md":
                            rules.append(f"{prefix}/{entry.name}" if prefix else entry.name)

                collect_rules(rules_dir, "")
        except OSError:
            pass

    # Count hooks (from settings.json or hooks/ directory)
    hook_count = 0
    if has_claude_dir:
        hooks_dir = claude_dir / "hooks"
        try:
            if hooks_dir.is_dir():
                hook_count = sum(1 for e in _safe_iterdir(hooks_dir) if e.is_file())
        except OSError:
            pass

        if hook_count == 0:
            settings_file = claude_dir / "settings.json"
            try:
                if settings_file.exists():
                    import orjson

                    content = _safe_read_file(settings_file)
                    parsed: Any = orjson.loads(content.encode())
                    if isinstance(parsed, dict):
                        hooks: Any = parsed.get("hooks")
                        if isinstance(hooks, dict):
                            hook_count = len(hooks)
            except (OSError, ValueError):
                pass

    # Detect keywords in CLAUDE.md content
    claude_md_keywords: list[str] = []
    if has_claude_md:
        detected: set[str] = set()
        for md_path in claude_md_paths:
            content = _safe_read_file(md_path).lower()
            if not content:
                continue
            for keyword, hint in _CLAUDE_MD_KEYWORDS.items():
                if keyword in content and hint not in detected:
                    detected.add(hint)
        claude_md_keywords = sorted(detected)

    return ProjectConfig(
        has_claude_dir=has_claude_dir,
        has_claude_md=has_claude_md,
        agents=sorted(agents),
        rules=sorted(rules),
        hook_count=hook_count,
        claude_md_keywords=claude_md_keywords,
    )


def parse_projects(project_dirs: list[str]) -> list[ProjectStats]:
    """Enumerate projects/ directory and build project stats for each entry."""
    stats: list[ProjectStats] = []

    for project_dir in project_dirs:
        path = Path(project_dir)
        encoded_path = path.name
        decoded_path = decode_project_path(encoded_path)
        session_count = _count_jsonl_files(path)
        memory_file_count = _count_memory_files(path)
        last_activity = _get_last_modified(path)

        # promptCount will be filled in by the conversations parser
        decoded = Path(decoded_path)
        is_dot_dir = decoded.name.startswith(".")
        tech_stack = [] if is_dot_dir else _scan_manifests(decoded)
        project_config = None if is_dot_dir else _scan_project_config(decoded)

        stats.append(
            ProjectStats(
                encoded_path=encoded_path,
                decoded_path=decoded_path,
                session_count=session_count,
                prompt_count=0,
                memory_file_count=memory_file_count,
                last_activity=last_activity,
                tech_stack=tech_stack if tech_stack else None,
                project_config=project_config,
            )
        )

    # Sort by lastActivity descending
    stats.sort(key=lambda s: s.last_activity, reverse=True)
    return stats
