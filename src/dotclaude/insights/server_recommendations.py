"""Server-side recommendation fetcher.

Calls GET /api/recommendations and returns a list of ServerRecommendation.
Falls back gracefully (returns None) when the user is not logged in,
the server is unreachable, or the response is malformed.
"""

from __future__ import annotations

import asyncio
import logging

from dotclaude_types.models import ServerRecommendation

from dotclaude.utils.api_client import AuthRequiredError, api_request

logger = logging.getLogger(__name__)

_DEFAULT_TOP_K = 7


def fetch_recommendations(top_k: int = _DEFAULT_TOP_K) -> list[ServerRecommendation] | None:
    """Fetch recommendations from the dotclaude server.

    Calls GET /api/recommendations?top_k=<top_k> with the stored access token.
    Returns None (instead of raising) when the token is absent, the server is
    unreachable, or the response cannot be parsed.

    Args:
        top_k: Maximum number of recommendations to request.

    Returns:
        List of ServerRecommendation on success, None otherwise.
    """
    try:
        return asyncio.run(_fetch_async(top_k))
    except Exception as exc:
        logger.warning("fetch_recommendations failed: %s", exc)
        return None


async def _fetch_async(top_k: int) -> list[ServerRecommendation] | None:
    """Async implementation — separated so the sync wrapper can call asyncio.run."""
    # AuthRequiredError means no token — silently return None
    try:
        res = await api_request(
            f"/api/recommendations?top_k={top_k}",
            method="GET",
        )
    except AuthRequiredError:
        logger.debug("fetch_recommendations: not logged in, skipping server call")
        return None
    except Exception as exc:
        logger.warning("fetch_recommendations: request error: %s", exc)
        return None

    if not res.is_success:
        logger.warning(
            "fetch_recommendations: server returned %d, skipping", res.status_code
        )
        return None

    try:
        raw: object = res.json()
    except Exception as exc:
        logger.warning("fetch_recommendations: failed to parse JSON: %s", exc)
        return None

    # envelope에서 recommendations 추출
    if isinstance(raw, dict):
        items = raw.get("recommendations", [])
    elif isinstance(raw, list):
        items = raw  # fallback for direct list response
    else:
        logger.warning(
            "fetch_recommendations: unexpected response type %s", type(raw).__name__
        )
        return None

    if not isinstance(items, list):
        logger.warning(
            "fetch_recommendations: recommendations field is not a list, got %s",
            type(items).__name__,
        )
        return None

    results: list[ServerRecommendation] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            results.append(ServerRecommendation.model_validate(item))
        except Exception as exc:
            logger.warning("fetch_recommendations: skipping invalid item: %s", exc)

    return results
