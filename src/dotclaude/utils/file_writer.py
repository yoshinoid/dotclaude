"""Safe file writer with path traversal protection and automatic backup."""

from __future__ import annotations

import shutil
import time
from pathlib import Path


def safe_write(base_dir: Path, target_path: str, content: str) -> str:
    """Write content to a file within base_dir safely.

    Applies three safety guarantees:
    1. Path traversal protection — only paths within base_dir are allowed.
    2. Automatic backup — existing files are preserved as .bak.{timestamp}.
    3. Parent directory creation — intermediate directories are created as needed.

    Args:
        base_dir: The root directory that all writes must stay within.
        target_path: Relative path from base_dir to the target file.
        content: UTF-8 text content to write.

    Returns:
        "created" if the file did not previously exist, "updated" if it did
        (in which case a .bak.{timestamp} backup was created alongside it).

    Raises:
        ValueError: If target_path resolves to a location outside base_dir.
    """
    resolved = (base_dir / target_path).resolve()
    if not resolved.is_relative_to(base_dir.resolve()):
        raise ValueError(f"Path traversal blocked: {target_path}")

    action = "created"
    if resolved.exists():
        backup = resolved.with_suffix(f"{resolved.suffix}.bak.{int(time.time())}")
        shutil.copy2(resolved, backup)
        action = "updated"

    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")
    return action
