"""Tests for formatting utilities.

Ported from TypeScript: src/__tests__/cli/formatters.test.ts
"""

from __future__ import annotations

from dotclaude.display.formatters import (
    format_bar,
    format_cost,
    format_number,
    format_percent,
    format_seconds,
    format_sparkline,
    format_tokens,
)


class TestFormatSparkline:
    def test_renders_sparkline_for_varying_values(self) -> None:
        result = format_sparkline([0, 5, 10, 5, 0], 5)
        assert len(result) == 5
        # First and last should be lowest char, middle should be highest
        assert result[0] == "\u2581"
        assert result[2] == "\u2588"
        assert result[4] == "\u2581"

    def test_handles_all_same_values(self) -> None:
        result = format_sparkline([5, 5, 5], 3)
        assert len(result) == 3
        # All same -> all minimum bar
        assert result == "\u2581\u2581\u2581"

    def test_handles_empty_array(self) -> None:
        assert format_sparkline([], 10) == ""

    def test_handles_zero_width(self) -> None:
        assert format_sparkline([1, 2, 3], 0) == ""

    def test_buckets_values_when_more_values_than_width(self) -> None:
        result = format_sparkline([0, 0, 10, 10, 0, 0], 3)
        assert len(result) == 3

    def test_handles_single_value(self) -> None:
        result = format_sparkline([42], 1)
        assert len(result) == 1


class TestFormatSeconds:
    def test_formats_seconds_only(self) -> None:
        assert format_seconds(45) == "45s"

    def test_formats_minutes_and_seconds(self) -> None:
        assert format_seconds(125) == "2m 5s"

    def test_formats_minutes_only_exact(self) -> None:
        assert format_seconds(120) == "2m"

    def test_formats_hours_and_minutes(self) -> None:
        assert format_seconds(3661) == "1h 1m"

    def test_formats_hours_only_exact(self) -> None:
        assert format_seconds(7200) == "2h"

    def test_formats_zero(self) -> None:
        assert format_seconds(0) == "0s"


class TestFormatPercent:
    def test_formats_ratio_as_percentage(self) -> None:
        assert format_percent(0.85) == "85.0%"

    def test_formats_zero(self) -> None:
        assert format_percent(0) == "0.0%"

    def test_formats_100_percent(self) -> None:
        assert format_percent(1) == "100.0%"

    def test_formats_small_values_with_precision(self) -> None:
        assert format_percent(0.1234) == "12.3%"


class TestFormatNumber:
    def test_formats_with_comma_separators(self) -> None:
        assert format_number(1234567) == "1,234,567"


class TestFormatTokens:
    def test_formats_millions(self) -> None:
        assert format_tokens(1200000) == "1.2M"

    def test_formats_thousands(self) -> None:
        assert format_tokens(450000) == "450K"

    def test_formats_small_numbers(self) -> None:
        assert format_tokens(890) == "890"


class TestFormatCost:
    def test_formats_as_usd(self) -> None:
        assert format_cost(12.34) == "$12.34"

    def test_formats_zero(self) -> None:
        assert format_cost(0) == "$0.00"


class TestFormatBar:
    def test_renders_full_bar_at_max(self) -> None:
        assert format_bar(10, 10, 5) == "\u2588\u2588\u2588\u2588\u2588"

    def test_renders_empty_bar_at_zero(self) -> None:
        assert format_bar(0, 10, 5) == "\u2591\u2591\u2591\u2591\u2591"

    def test_handles_max_zero(self) -> None:
        assert format_bar(0, 0, 5) == "\u2591\u2591\u2591\u2591\u2591"
