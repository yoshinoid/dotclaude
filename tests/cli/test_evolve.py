"""Tests for --evolve RAG upgrade.

Covers:
1. Server success  — fetch_recommendations returns server results
2. Server failure  — fetch_recommendations returns None → local-only fallback
3. Server + local merge — dedup, max 7 cap
4. No token (AuthRequiredError) — local only, server call skipped
5. Empty server response — 0 items → local only
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from dotclaude_types.models import Recommendation, ServerRecommendation

from dotclaude.insights.merge import MAX_TOTAL, merge_recommendations
from dotclaude.insights.server_recommendations import fetch_recommendations

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_server_rec(
    title: str = "Python Rules",
    type_: str = "rule",
    score: float = 0.90,
    reason: str = "high cache miss rate",
) -> ServerRecommendation:
    return ServerRecommendation(
        knowledgeId="kid-1",
        title=title,
        type=type_,  # type: ignore[arg-type]
        stack=["python"],
        snippet="first 200 chars...",
        score=score,
        reason=reason,
        source="rag",
    )


def _make_local_rec(
    name: str = "Docker Rules",
    type_: str = "rule",
    confidence: str = "medium",
) -> Recommendation:
    return Recommendation(
        catalogId="docker",
        type=type_,  # type: ignore[arg-type]
        name=name,
        description="Docker best practices",
        reason="docker stack detected",
        project=None,
        confidence=confidence,  # type: ignore[arg-type]
        actionPath="~/.claude/rules/devops/docker.md",
    )


# ---------------------------------------------------------------------------
# Task 12-1: Server success
# ---------------------------------------------------------------------------


def test_fetch_recommendations_success() -> None:
    """fetch_recommendations parses server JSON into ServerRecommendation list."""
    raw_response = [
        {
            "knowledgeId": "kid-1",
            "title": "Python Rules",
            "type": "rule",
            "stack": ["python"],
            "snippet": "some text",
            "score": 0.92,
            "reason": "python stack detected",
            "source": "rag",
        }
    ]

    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = raw_response

    with patch(
        "dotclaude.insights.server_recommendations.api_request",
        new=AsyncMock(return_value=mock_response),
    ):
        result = fetch_recommendations(top_k=7)

    assert result is not None
    assert len(result) == 1
    assert result[0].title == "Python Rules"
    assert result[0].score == pytest.approx(0.92)


# ---------------------------------------------------------------------------
# Task 12-2: Server failure → local fallback
# ---------------------------------------------------------------------------


def test_fetch_recommendations_server_error_returns_none() -> None:
    """When server returns non-success, fetch_recommendations returns None."""
    mock_response = MagicMock()
    mock_response.is_success = False
    mock_response.status_code = 500

    with patch(
        "dotclaude.insights.server_recommendations.api_request",
        new=AsyncMock(return_value=mock_response),
    ):
        result = fetch_recommendations()

    assert result is None


def test_merge_server_failure_uses_local_only() -> None:
    """merge_recommendations with server=None yields only local items."""
    local = [_make_local_rec("Docker Rules"), _make_local_rec("CI/CD Rules", type_="rule")]
    merged, server_count, local_count = merge_recommendations(None, local)

    assert server_count == 0
    assert local_count == 2
    assert all(m.source == "local" for m in merged)


# ---------------------------------------------------------------------------
# Task 12-3: Server + local merge (dedup, max 7)
# ---------------------------------------------------------------------------


def test_merge_server_plus_local_dedup_and_cap() -> None:
    """Server items go first; local supplements; duplicates removed; max 7."""
    server = [_make_server_rec(f"Rule {i}", score=0.9 - i * 0.05) for i in range(5)]
    # Two local items — one overlaps with server (same type+title), one is new
    local = [
        _make_local_rec("Rule 0"),  # duplicate of server item 0 → should be skipped
        _make_local_rec("Docker Rules"),  # new
        _make_local_rec("CI/CD Rules"),  # new
    ]
    merged, server_count, local_count = merge_recommendations(server, local)

    assert server_count == 5
    assert local_count == 2
    assert len(merged) == 7

    titles = [m.title for m in merged]
    # Server items come first
    assert titles[:5] == [f"Rule {i}" for i in range(5)]
    # Local supplement after
    assert "Docker Rules" in titles
    assert "CI/CD Rules" in titles
    # No duplicate
    assert titles.count("Rule 0") == 1


def test_merge_respects_max_total() -> None:
    """Total merged count never exceeds MAX_TOTAL."""
    server = [_make_server_rec(f"S{i}") for i in range(6)]
    local = [_make_local_rec(f"L{i}") for i in range(6)]
    merged, _, _ = merge_recommendations(server, local)

    assert len(merged) <= MAX_TOTAL


# ---------------------------------------------------------------------------
# Task 12-4: No token → local only (server call skipped)
# ---------------------------------------------------------------------------


def test_fetch_recommendations_no_token_returns_none() -> None:
    """AuthRequiredError from api_request → fetch_recommendations returns None."""
    from dotclaude.utils.api_client import AuthRequiredError

    with patch(
        "dotclaude.insights.server_recommendations.api_request",
        new=AsyncMock(side_effect=AuthRequiredError()),
    ):
        result = fetch_recommendations()

    assert result is None


def test_merge_no_token_uses_local() -> None:
    """When fetch returns None (no token), merge produces local-only output."""
    local = [_make_local_rec("Python Rules", type_="rule")]
    merged, server_count, local_count = merge_recommendations(None, local)

    assert server_count == 0
    assert local_count == 1
    assert merged[0].source == "local"


# ---------------------------------------------------------------------------
# Task 12-5: Empty server response → local only
# ---------------------------------------------------------------------------


def test_fetch_recommendations_empty_list() -> None:
    """Server returns empty list → fetch_recommendations returns empty list (not None)."""
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = []

    with patch(
        "dotclaude.insights.server_recommendations.api_request",
        new=AsyncMock(return_value=mock_response),
    ):
        result = fetch_recommendations()

    assert result == []


def test_merge_empty_server_uses_local() -> None:
    """Empty server list → all slots filled by local catalog."""
    local = [_make_local_rec("Docker Rules"), _make_local_rec("CI/CD Rules")]
    merged, server_count, local_count = merge_recommendations([], local)

    assert server_count == 0
    assert local_count == 2
    assert all(m.source == "local" for m in merged)


# ---------------------------------------------------------------------------
# Additional: MergedRecommendation source field correctness
# ---------------------------------------------------------------------------


def test_merged_recommendation_source_labels() -> None:
    """Server items are labeled 'server', local items are labeled 'local'."""
    server = [_make_server_rec("FastAPI Rules", type_="rule", score=0.87)]
    local = [_make_local_rec("Docker Rules")]
    merged, server_count, local_count = merge_recommendations(server, local)

    assert merged[0].source == "server"
    assert merged[0].title == "FastAPI Rules"
    assert merged[0].score == pytest.approx(0.87)

    assert merged[1].source == "local"
    assert merged[1].title == "Docker Rules"
    assert merged[1].score is None


def test_merge_score_preserved_for_server() -> None:
    """Score from ServerRecommendation is preserved in MergedRecommendation."""
    srv = _make_server_rec("planner", type_="agent", score=0.81)
    merged, _, _ = merge_recommendations([srv], [])
    assert merged[0].score == pytest.approx(0.81)


def test_fetch_recommendations_envelope_format() -> None:
    """Server returns envelope dict — recommendations extracted correctly."""
    raw_response = {
        "snapshot_id": "abc-123",
        "cached": False,
        "recommendations": [
            {
                "knowledgeId": "kid-1",
                "title": "Python Rules",
                "type": "rule",
                "stack": ["python"],
                "snippet": "some text",
                "score": 0.92,
                "reason": "python stack detected",
                "source": "rag",
            }
        ],
    }

    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = raw_response

    with patch(
        "dotclaude.insights.server_recommendations.api_request",
        new=AsyncMock(return_value=mock_response),
    ):
        result = fetch_recommendations()

    assert result is not None
    assert len(result) == 1
    assert result[0].title == "Python Rules"


def test_fetch_recommendations_unexpected_type_returns_none() -> None:
    """When server response is neither dict nor list, fetch_recommendations returns None."""
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = 42  # unexpected type

    with patch(
        "dotclaude.insights.server_recommendations.api_request",
        new=AsyncMock(return_value=mock_response),
    ):
        result = fetch_recommendations()

    assert result is None
