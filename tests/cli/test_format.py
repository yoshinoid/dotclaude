"""Tests for the format command (dotclaude format)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.exceptions import Exit as ClickExit
from typer.testing import CliRunner

from dotclaude.cli import app
from dotclaude.commands.format import TYPE_GLOBS, _collect_files, run_format

runner = CliRunner()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PLAIN_MD = "# Test Rule\n\nSome content here.\n"

_FRONTED_MD = """\
---
dc_type: rule
dc_stack: []
dc_scope: global
dc_description: Test Rule
---

# Test Rule

Some content here.
"""


def _make_claude_dir(tmp_path: Path) -> Path:
    """Create a minimal ~/.claude-like directory structure."""
    base = tmp_path / ".claude"
    (base / "agents").mkdir(parents=True)
    (base / "rules").mkdir(parents=True)
    (base / "skills" / "my-skill").mkdir(parents=True)
    (base / "commands").mkdir(parents=True)
    return base


# ---------------------------------------------------------------------------
# TYPE_GLOBS public constant
# ---------------------------------------------------------------------------


class TestTypeGlobs:
    def test_type_globs_is_public(self) -> None:
        """TYPE_GLOBS must be importable without underscore prefix (S1 fix)."""
        assert TYPE_GLOBS is not None
        assert len(TYPE_GLOBS) > 0

    def test_type_globs_covers_all_types(self) -> None:
        """TYPE_GLOBS must include all four known file types."""
        types = {ft for ft, _ in TYPE_GLOBS}
        assert types == {"agent", "rule", "skill", "command"}

    def test_type_globs_importable_from_sync(self) -> None:
        """sync.py must be able to import TYPE_GLOBS from format.py."""
        from dotclaude.commands.sync import _collect_knowledge_items  # noqa: F401

        # If the import in sync.py is broken, this would raise ImportError
        import dotclaude.commands.sync as sync_module

        assert hasattr(sync_module, "_collect_knowledge_items")


# ---------------------------------------------------------------------------
# _collect_files unit tests
# ---------------------------------------------------------------------------


class TestCollectFiles:
    def test_collects_agents(self, tmp_path: Path) -> None:
        base = _make_claude_dir(tmp_path)
        (base / "agents" / "agent.md").write_text(_PLAIN_MD, encoding="utf-8")

        result = _collect_files(base, type_filter=None)

        assert any(ft == "agent" and p.name == "agent.md" for ft, p in result)

    def test_collects_rules(self, tmp_path: Path) -> None:
        base = _make_claude_dir(tmp_path)
        (base / "rules" / "python.md").write_text(_PLAIN_MD, encoding="utf-8")

        result = _collect_files(base, type_filter=None)

        assert any(ft == "rule" and p.name == "python.md" for ft, p in result)

    def test_collects_skills(self, tmp_path: Path) -> None:
        base = _make_claude_dir(tmp_path)
        (base / "skills" / "my-skill" / "SKILL.md").write_text(_PLAIN_MD, encoding="utf-8")

        result = _collect_files(base, type_filter=None)

        assert any(ft == "skill" and p.name == "SKILL.md" for ft, p in result)

    def test_collects_commands(self, tmp_path: Path) -> None:
        base = _make_claude_dir(tmp_path)
        (base / "commands" / "plan.md").write_text(_PLAIN_MD, encoding="utf-8")

        result = _collect_files(base, type_filter=None)

        assert any(ft == "command" and p.name == "plan.md" for ft, p in result)

    def test_type_filter_restricts_to_rule(self, tmp_path: Path) -> None:
        base = _make_claude_dir(tmp_path)
        (base / "agents" / "agent.md").write_text(_PLAIN_MD, encoding="utf-8")
        (base / "rules" / "python.md").write_text(_PLAIN_MD, encoding="utf-8")

        result = _collect_files(base, type_filter="rule")

        types = {ft for ft, _ in result}
        assert types == {"rule"}

    def test_empty_directory_returns_empty_list(self, tmp_path: Path) -> None:
        base = _make_claude_dir(tmp_path)

        result = _collect_files(base, type_filter=None)

        assert result == []

    def test_nested_rules_collected(self, tmp_path: Path) -> None:
        base = _make_claude_dir(tmp_path)
        nested = base / "rules" / "backend"
        nested.mkdir(parents=True)
        (nested / "python.md").write_text(_PLAIN_MD, encoding="utf-8")

        result = _collect_files(base, type_filter=None)

        assert any(ft == "rule" and p.name == "python.md" for ft, p in result)


# ---------------------------------------------------------------------------
# run_format unit tests (format_file is mocked)
# ---------------------------------------------------------------------------


def _make_format_result(
    path: str,
    action: str = "added",
) -> MagicMock:
    """Build a mock FormatResult."""
    result = MagicMock()
    result.path = path
    result.action = action
    return result


class TestRunFormat:
    def test_basic_run_adds_frontmatter(self, tmp_path: Path) -> None:
        base = _make_claude_dir(tmp_path)
        rule_file = base / "rules" / "test.md"
        rule_file.write_text(_PLAIN_MD, encoding="utf-8")

        with patch("dotclaude.commands.format.format_file") as mock_ff:
            mock_ff.return_value = _make_format_result(str(rule_file), "added")
            run_format(path=str(base))

        mock_ff.assert_called_once_with(str(rule_file), force=False, dry_run=False)

    def test_dry_run_does_not_write(self, tmp_path: Path) -> None:
        base = _make_claude_dir(tmp_path)
        rule_file = base / "rules" / "test.md"
        rule_file.write_text(_PLAIN_MD, encoding="utf-8")

        original_content = rule_file.read_text(encoding="utf-8")

        with patch("dotclaude.commands.format.format_file") as mock_ff:
            mock_ff.return_value = _make_format_result(str(rule_file), "added")
            run_format(path=str(base), dry_run=True)

        # dry_run=True must be forwarded to format_file
        mock_ff.assert_called_once_with(str(rule_file), force=False, dry_run=True)
        # Actual file is untouched (format_file is mocked, so content unchanged)
        assert rule_file.read_text(encoding="utf-8") == original_content

    def test_force_flag_forwarded(self, tmp_path: Path) -> None:
        base = _make_claude_dir(tmp_path)
        agent_file = base / "agents" / "planner.md"
        agent_file.write_text(_FRONTED_MD, encoding="utf-8")

        with patch("dotclaude.commands.format.format_file") as mock_ff:
            mock_ff.return_value = _make_format_result(str(agent_file), "updated")
            run_format(path=str(base), force=True)

        mock_ff.assert_called_once_with(str(agent_file), force=True, dry_run=False)

    def test_type_filter_agent_ignores_rules(self, tmp_path: Path) -> None:
        base = _make_claude_dir(tmp_path)
        rule_file = base / "rules" / "test.md"
        rule_file.write_text(_PLAIN_MD, encoding="utf-8")
        agent_file = base / "agents" / "planner.md"
        agent_file.write_text(_PLAIN_MD, encoding="utf-8")

        with patch("dotclaude.commands.format.format_file") as mock_ff:
            mock_ff.return_value = _make_format_result(str(agent_file), "added")
            run_format(path=str(base), type_filter="agent")

        # format_file should only be called for the agent file
        assert mock_ff.call_count == 1
        called_path = mock_ff.call_args[0][0]
        assert "agents" in called_path

    def test_empty_directory_no_error(self, tmp_path: Path) -> None:
        base = _make_claude_dir(tmp_path)

        # Should not raise
        with patch("dotclaude.commands.format.format_file") as mock_ff:
            run_format(path=str(base))

        mock_ff.assert_not_called()

    def test_nonexistent_path_exits(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent"

        with pytest.raises(ClickExit) as exc_info:
            run_format(path=str(missing))

        assert exc_info.value.exit_code == 1

    def test_invalid_type_filter_exits(self, tmp_path: Path) -> None:
        base = _make_claude_dir(tmp_path)

        with pytest.raises(ClickExit) as exc_info:
            run_format(path=str(base), type_filter="invalid_type")

        assert exc_info.value.exit_code == 1

    def test_skipped_files_counted(self, tmp_path: Path) -> None:
        base = _make_claude_dir(tmp_path)
        rule_file = base / "rules" / "test.md"
        rule_file.write_text(_FRONTED_MD, encoding="utf-8")

        with patch("dotclaude.commands.format.format_file") as mock_ff:
            mock_ff.return_value = _make_format_result(str(rule_file), "skipped")
            # Should complete without error even when all files are skipped
            run_format(path=str(base))

        mock_ff.assert_called_once()

    def test_format_file_exception_does_not_abort(self, tmp_path: Path) -> None:
        base = _make_claude_dir(tmp_path)
        rule1 = base / "rules" / "a.md"
        rule2 = base / "rules" / "b.md"
        rule1.write_text(_PLAIN_MD, encoding="utf-8")
        rule2.write_text(_PLAIN_MD, encoding="utf-8")

        call_count = 0

        def _side_effect(path: str, **_kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if "a.md" in path:
                raise OSError("read error")
            return _make_format_result(path, "added")

        with patch("dotclaude.commands.format.format_file", side_effect=_side_effect):
            run_format(path=str(base))

        # Both files attempted; exception on first should not prevent second
        assert call_count == 2


# ---------------------------------------------------------------------------
# CLI integration tests (Typer test runner)
# ---------------------------------------------------------------------------


class TestFormatCLI:
    def test_cli_dry_run_flag(self, tmp_path: Path) -> None:
        base = _make_claude_dir(tmp_path)
        (base / "rules" / "test.md").write_text(_PLAIN_MD, encoding="utf-8")

        with patch("dotclaude.commands.format.format_file") as mock_ff:
            mock_ff.return_value = _make_format_result(
                str(base / "rules" / "test.md"), "added"
            )
            result = runner.invoke(app, ["format", str(base), "--dry-run"])

        assert result.exit_code == 0
        assert "Preview" in result.output or "preview" in result.output.lower()

    def test_cli_type_option(self, tmp_path: Path) -> None:
        base = _make_claude_dir(tmp_path)
        (base / "agents" / "planner.md").write_text(_PLAIN_MD, encoding="utf-8")

        with patch("dotclaude.commands.format.format_file") as mock_ff:
            mock_ff.return_value = _make_format_result(
                str(base / "agents" / "planner.md"), "added"
            )
            result = runner.invoke(app, ["format", str(base), "--type", "agent"])

        assert result.exit_code == 0

    def test_cli_invalid_type_exits_nonzero(self, tmp_path: Path) -> None:
        base = _make_claude_dir(tmp_path)

        result = runner.invoke(app, ["format", str(base), "--type", "bogus"])

        assert result.exit_code != 0

    def test_cli_missing_path_exits_nonzero(self, tmp_path: Path) -> None:
        missing = tmp_path / "nope"

        result = runner.invoke(app, ["format", str(missing)])

        assert result.exit_code != 0
