"""Tests for parser.utils, ported from TypeScript utils.test.ts."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from dotclaude.parser.utils import (
    decode_project_path,
    normalize_cwd,
    safe_json_parse,
    stream_jsonl,
)

SEP = os.sep

# ---------------------------------------------------------------------------
# decode_project_path
# ---------------------------------------------------------------------------


class TestDecodeProjectPath:
    def test_decodes_windows_absolute_path_with_drive_letter(self) -> None:
        result = decode_project_path("C--Users-jeong-projects-foo")
        assert result == f"C:\\Users{SEP}jeong{SEP}projects{SEP}foo"

    def test_decodes_path_with_dot_encoded_as_double_hyphen(self) -> None:
        result = decode_project_path("C--Users-jeong--claude")
        assert result == f"C:\\Users{SEP}jeong{SEP}.claude"

    def test_decodes_unix_style_path_without_drive_letter(self) -> None:
        result = decode_project_path("Users-jeong--claude")
        assert result == f"Users{SEP}jeong{SEP}.claude"

    def test_handles_single_segment_encoded_path(self) -> None:
        assert decode_project_path("myproject") == "myproject"

    def test_handles_empty_string_gracefully(self) -> None:
        assert decode_project_path("") == ""

    def test_decodes_deep_nested_path_with_multiple_segments(self) -> None:
        result = decode_project_path("C--Users-jeong-projects-dotclaude")
        assert result == f"C:\\Users{SEP}jeong{SEP}projects{SEP}dotclaude"

    def test_handles_lowercase_drive_letter(self) -> None:
        result = decode_project_path("c--users-jeong")
        assert result == f"c:\\users{SEP}jeong"


# ---------------------------------------------------------------------------
# safe_json_parse
# ---------------------------------------------------------------------------


class TestSafeJsonParse:
    def test_parses_valid_json_object(self) -> None:
        result = safe_json_parse('{"key":"value"}')
        assert result == {"key": "value"}

    def test_parses_valid_json_array(self) -> None:
        result = safe_json_parse("[1,2,3]")
        assert result == [1, 2, 3]

    def test_parses_valid_json_string(self) -> None:
        result = safe_json_parse('"hello"')
        assert result == "hello"

    def test_parses_valid_json_number(self) -> None:
        result = safe_json_parse("42")
        assert result == 42

    def test_returns_none_for_invalid_json(self) -> None:
        assert safe_json_parse("{invalid}") is None

    def test_returns_none_for_empty_string(self) -> None:
        assert safe_json_parse("") is None

    def test_returns_none_for_truncated_json(self) -> None:
        assert safe_json_parse('{"key":') is None

    def test_parses_null_literal(self) -> None:
        # orjson returns None for "null", which is correct JSON
        # TS version returns null for "null" (same semantics)
        result = safe_json_parse("null")
        assert result is None


# ---------------------------------------------------------------------------
# stream_jsonl
# ---------------------------------------------------------------------------


class TestStreamJsonl:
    def test_streams_all_valid_records(self, tmp_dir: Path) -> None:
        file_path = tmp_dir / "test.jsonl"
        lines = [
            json.dumps({"type": "assistant", "id": "1"}),
            json.dumps({"type": "user", "id": "2"}),
            json.dumps({"type": "assistant", "id": "3"}),
        ]
        file_path.write_text("\n".join(lines), encoding="utf-8")

        records = list(stream_jsonl(file_path))

        assert len(records) == 3
        assert records[0] == {"type": "assistant", "id": "1"}
        assert records[1] == {"type": "user", "id": "2"}
        assert records[2] == {"type": "assistant", "id": "3"}

    def test_skips_blank_lines_silently(self, tmp_dir: Path) -> None:
        file_path = tmp_dir / "blanks.jsonl"
        file_path.write_text(
            "\n".join([json.dumps({"id": "1"}), "", "   ", json.dumps({"id": "2"})]),
            encoding="utf-8",
        )

        records = list(stream_jsonl(file_path))
        assert len(records) == 2

    def test_skips_malformed_json_lines_without_crashing(self, tmp_dir: Path) -> None:
        file_path = tmp_dir / "malformed.jsonl"
        file_path.write_text(
            "\n".join(
                [json.dumps({"id": "1"}), "{not valid json", json.dumps({"id": "2"})]
            ),
            encoding="utf-8",
        )

        records = list(stream_jsonl(file_path))
        assert len(records) == 2
        assert records[0]["id"] == "1"
        assert records[1]["id"] == "2"

    def test_handles_empty_file(self, tmp_dir: Path) -> None:
        file_path = tmp_dir / "empty.jsonl"
        file_path.write_text("", encoding="utf-8")

        records = list(stream_jsonl(file_path))
        assert len(records) == 0

    def test_raises_when_file_does_not_exist(self, tmp_dir: Path) -> None:
        file_path = tmp_dir / "nonexistent.jsonl"
        with pytest.raises((FileNotFoundError, OSError)):
            list(stream_jsonl(file_path))

    def test_handles_crlf_line_endings(self, tmp_dir: Path) -> None:
        file_path = tmp_dir / "crlf.jsonl"
        content = "\r\n".join([json.dumps({"id": "1"}), json.dumps({"id": "2"})])
        file_path.write_bytes(content.encode("utf-8"))

        records = list(stream_jsonl(file_path))
        assert len(records) == 2

    def test_processes_large_number_of_records(self, tmp_dir: Path) -> None:
        file_path = tmp_dir / "large.jsonl"
        line_count = 1000
        lines = [json.dumps({"index": i, "value": f"item-{i}"}) for i in range(line_count)]
        file_path.write_text("\n".join(lines), encoding="utf-8")

        count = sum(1 for _ in stream_jsonl(file_path))
        assert count == line_count


# ---------------------------------------------------------------------------
# normalize_cwd
# ---------------------------------------------------------------------------


class TestNormalizeCwd:
    def test_lowercases_entire_windows_path(self) -> None:
        assert normalize_cwd("C:/Users/Jeong/Projects") == "c:/users/jeong/projects"

    def test_converts_backslashes_to_forward_slashes(self) -> None:
        assert normalize_cwd("C:\\Users\\Jeong\\projects") == "c:/users/jeong/projects"

    def test_removes_trailing_slash(self) -> None:
        assert normalize_cwd("C:/Users/jeong/projects/") == "c:/users/jeong/projects"

    def test_lowercases_unix_paths(self) -> None:
        assert normalize_cwd("/Users/Jeong/Projects") == "/users/jeong/projects"

    def test_handles_empty_string(self) -> None:
        assert normalize_cwd("") == ""

    def test_preserves_root_slash(self) -> None:
        assert normalize_cwd("/") == "/"
