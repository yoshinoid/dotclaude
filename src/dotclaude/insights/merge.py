"""Merge server recommendations with local catalog recommendations.

Server recommendations take priority.  Local catalog items fill the remaining
slots (up to MAX_TOTAL) when the server response is absent or sparse.
Deduplication is done by (type, title) pair — case-insensitive.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from dotclaude_types.models import Recommendation, ServerRecommendation

MAX_TOTAL = 7


@dataclass(frozen=True)
class MergedRecommendation:
    """Unified view of a recommendation regardless of its origin."""

    type: str
    title: str
    description: str
    score: float | None
    reason: str
    action_path: str | None
    source: Literal["server", "local"]


def _dedup_key(type_: str, title: str) -> str:
    return f"{type_.lower()}:{title.lower()}"


def merge_recommendations(
    server: list[ServerRecommendation] | None,
    local: list[Recommendation],
    max_total: int = MAX_TOTAL,
) -> tuple[list[MergedRecommendation], int, int]:
    """Merge server and local recommendations.

    Args:
        server: List from the server API (may be None when unavailable).
        local: List from the local catalog engine.
        max_total: Hard cap on total returned items.

    Returns:
        A 3-tuple of:
        - merged list (server-first, then local supplement)
        - count of server-origin items
        - count of local-origin items
    """
    merged: list[MergedRecommendation] = []
    seen: set[str] = set()

    # --- server recommendations go first ---
    if server:
        for srv in server:
            if len(merged) >= max_total:
                break
            key = _dedup_key(srv.type, srv.title)
            if key in seen:
                continue
            seen.add(key)
            merged.append(
                MergedRecommendation(
                    type=srv.type,
                    title=srv.title,
                    description=srv.snippet or srv.reason,
                    score=srv.score,
                    reason=srv.reason,
                    action_path=None,
                    source="server",
                )
            )

    server_count = len(merged)

    # --- local catalog fills remaining slots ---
    for loc in local:
        if len(merged) >= max_total:
            break
        key = _dedup_key(loc.type, loc.name)
        if key in seen:
            continue
        seen.add(key)
        merged.append(
            MergedRecommendation(
                type=loc.type,
                title=loc.name,
                description=loc.description,
                score=None,
                reason=loc.reason,
                action_path=loc.action_path,
                source="local",
            )
        )

    local_count = len(merged) - server_count
    return merged, server_count, local_count
