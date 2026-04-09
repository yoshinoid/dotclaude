"""Formatting utilities for the dotclaude CLI dashboard.

All functions handle 0/null/undefined gracefully.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timezone


def format_number(n: int | float) -> str:
    """Format a number with comma separators.

    Example: format_number(1234567) => "1,234,567"
    """
    return f"{int(n):,}"


def format_tokens(n: int | float) -> str:
    """Format a token count as a human-readable string.

    Example: format_tokens(1200000) => "1.2M"
    Example: format_tokens(450000) => "450K"
    Example: format_tokens(890) => "890"
    """
    n_int = int(n)
    if n_int >= 1_000_000:
        return f"{n_int / 1_000_000:.1f}M"
    if n_int >= 1_000:
        return f"{round(n_int / 1_000)}K"
    return str(n_int)


def format_cost(n: float) -> str:
    """Format a cost value as USD.

    Example: format_cost(12.34) => "$12.34"
    """
    return f"${n:.2f}"


def format_date(iso: str) -> str:
    """Format an ISO date string as a relative human-readable string.

    Example: format_date("2025-04-06T...") => "2d ago"
    Example: format_date("2025-04-08T...") => "today"
    """
    epoch_iso = datetime.fromtimestamp(0, tz=timezone.utc).isoformat()
    if not iso or iso == epoch_iso:
        return "\u2014"

    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return "\u2014"

    today = date.today()
    target_date = dt.date()
    diff_days = (today - target_date).days

    if diff_days == 0:
        return "today"
    if diff_days == 1:
        return "yesterday"
    if diff_days < 30:
        return f"{diff_days}d ago"

    return dt.strftime("%b %-d") if hasattr(dt, "strftime") else iso[:10]


def format_bar(value: float, max_value: float, width: int) -> str:
    """Render a horizontal text bar chart.

    Uses block characters: filled = '\u2588', empty = '\u2591'
    """
    if max_value == 0 or width <= 0:
        return "\u2591" * width
    filled = round((value / max_value) * width)
    empty = width - filled
    return "\u2588" * filled + "\u2591" * empty


def format_sparkline(values: list[float], width: int) -> str:
    """Render a sparkline chart from an array of numbers.

    Uses Unicode block characters: \u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588
    """
    if not values or width <= 0:
        return ""

    chars = "\u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"

    # Bucket values if there are more values than width
    if len(values) > width:
        bucket_size = len(values) / width
        bucketed: list[float] = []
        for i in range(width):
            start = math.floor(i * bucket_size)
            end = math.floor((i + 1) * bucket_size)
            bucket = values[start:end]
            bucketed.append(sum(bucket) / len(bucket) if bucket else 0.0)
    else:
        bucketed = list(values)

    min_val = min(bucketed)
    max_val = max(bucketed)
    value_range = max_val - min_val

    result = []
    for v in bucketed:
        if value_range == 0:
            result.append(chars[0])
        else:
            idx = round(((v - min_val) / value_range) * (len(chars) - 1))
            result.append(chars[idx])

    return "".join(result)


def format_seconds(total_sec: int | float) -> str:
    """Format seconds into a human-readable duration string.

    Example: format_seconds(3661) => "1h 1m"
    Example: format_seconds(125) => "2m 5s"
    Example: format_seconds(45) => "45s"
    """
    total_sec = int(total_sec)
    if total_sec < 60:
        return f"{total_sec}s"

    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    seconds = total_sec % 60

    if hours > 0:
        return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
    return f"{minutes}m {seconds}s" if seconds > 0 else f"{minutes}m"


def format_percent(ratio: float) -> str:
    """Format a ratio as a percentage string.

    Example: format_percent(0.85) => "85.0%"
    """
    return f"{ratio * 100:.1f}%"


def short_model(model: str) -> str:
    """Shorten model name for display.

    "claude-opus-4-6" -> "opus-4-6"
    "claude-sonnet-4-5-20250514" -> "sonnet-4-5"
    """
    import re

    short = model.removeprefix("claude-")
    short = re.sub(r"-\d{8}$", "", short)
    return short


def format_duration(start_iso: str, end_iso: str) -> str:
    """Format a date range period from two ISO strings.

    Example: format_duration("2025-03-24T...", "2025-04-08T...") => "Mar 24 \u2013 Apr 8"
    """
    epoch_iso = datetime.fromtimestamp(0, tz=timezone.utc).isoformat()
    if not start_iso or start_iso == epoch_iso or not end_iso or end_iso == epoch_iso:
        return "\u2014"

    try:
        start = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
    except ValueError:
        return "\u2014"

    def fmt(d: datetime) -> str:
        return d.strftime("%b %-d") if hasattr(d, "strftime") else d.isoformat()[:10]

    return f"{fmt(start)} \u2013 {fmt(end)}"
