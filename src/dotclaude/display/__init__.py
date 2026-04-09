"""Display package — dashboard, formatters, and HTML report."""

from __future__ import annotations

from dotclaude.display.dashboard import render_dashboard
from dotclaude.display.formatters import (
    format_bar,
    format_cost,
    format_date,
    format_duration,
    format_number,
    format_percent,
    format_seconds,
    format_sparkline,
    format_tokens,
    short_model,
)
from dotclaude.display.html_report import render_html

__all__ = [
    "render_dashboard",
    "render_html",
    "format_bar",
    "format_cost",
    "format_date",
    "format_duration",
    "format_number",
    "format_percent",
    "format_seconds",
    "format_sparkline",
    "format_tokens",
    "short_model",
]
