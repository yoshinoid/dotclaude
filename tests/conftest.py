"""Shared test fixtures for dotclaude tests."""

from __future__ import annotations

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture
def tmp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory(prefix="dotclaude-test-") as d:
        yield Path(d)


@pytest.fixture
def claude_dir(tmp_dir: Path) -> Path:
    """Create a mock ~/.claude directory structure."""
    claude = tmp_dir / "dotclaude"
    claude.mkdir()
    (claude / "projects").mkdir()
    (claude / "sessions").mkdir()
    return claude
