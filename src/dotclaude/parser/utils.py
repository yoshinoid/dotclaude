"""Parser utility functions ported from TypeScript utils.ts."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path
from typing import Any

import orjson


def get_claude_dir() -> Path:
    """Return the cross-platform path to the ~/.claude directory."""
    return Path.home() / ".claude"


def safe_json_parse(line: str) -> Any | None:
    """Safely parse a JSON string. Returns None on any parse error."""
    try:
        return orjson.loads(line)
    except (orjson.JSONDecodeError, ValueError):
        return None


def stream_jsonl(path: Path) -> Generator[Any, None, None]:
    """Stream a JSONL file line-by-line without loading the entire file into memory.

    Yields each successfully parsed JSON object.
    Blank lines and malformed JSON are silently skipped.

    Raises:
        FileNotFoundError: If the file does not exist.
        OSError: If the file cannot be opened.
    """
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            parsed = safe_json_parse(stripped)
            if parsed is not None:
                yield parsed


def normalize_cwd(cwd: str) -> str:
    """Normalize a cwd or file path for case-insensitive comparison.

    Windows and macOS have case-insensitive filesystems by default,
    so all paths are lowercased for reliable matching.
    Backslashes are converted to forward slashes, trailing slash removed.
    """
    if not cwd:
        return ""
    result = cwd.replace("\\", "/").lower()
    # Remove trailing slash (but not root "/")
    if len(result) > 1 and result.endswith("/"):
        result = result[:-1]
    return result


def decode_project_path(encoded: str) -> str:
    """Decode a Claude project encoded directory name back to a human-readable path.

    Encoding rules observed in the wild:
      - Windows drive letter: ``C--Users-...`` → ``C:\\Users\\...``
        The first ``--`` following the drive letter stands for ``:\\``
      - Path separators ``/`` or ``\\`` are encoded as single ``-``
      - A dot (``.``) at the start of a segment is encoded as ``--`` prefix
        e.g. ``.claude`` → ``--claude``, so ``X-Y--claude`` → ``X\\Y\\.claude``
    """
    if not encoded:
        return ""

    import re

    # Detect Windows drive prefix: single letter followed by --
    drive_match = re.match(r"^([A-Za-z])--", encoded)

    if drive_match is not None:
        drive_letter = drive_match.group(1)
        prefix = f"{drive_letter}:\\"
        rest = encoded[len(drive_match.group(0)):]  # strip "X--"
    else:
        prefix = ""
        rest = encoded

    # Split on single `-`. Consecutive `--` in the source becomes an empty
    # token between two `-` delimiters, which we detect and replace with `.`.
    parts = rest.split("-")
    segments: list[str] = []

    i = 0
    while i < len(parts):
        part = parts[i]
        if part == "" and i + 1 < len(parts):
            # `--` sequence: empty token means the next token is a dot-prefixed name
            next_part = parts[i + 1]
            segments.append(f".{next_part}")
            i += 2
        else:
            segments.append(part)
            i += 1

    return prefix + os.sep.join(segments)
