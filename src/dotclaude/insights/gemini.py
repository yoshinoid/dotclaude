"""Gemini API client.

Uses httpx (async), JSON mode, 30s timeout, explicit error handling.
API key is sent via x-goog-api-key header (not URL query string) to prevent
accidental exposure in proxy/CDN logs.
"""

from __future__ import annotations

from typing import Any

import httpx
from dotclaude_types.models import GeminiInsightsResponse

_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash:generateContent"
)


class GeminiError(Exception):
    """Raised when a Gemini API call fails."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _extract_response_text(body: Any) -> str | None:
    """Extract the text from the Gemini API response body."""
    if not isinstance(body, dict):
        return None
    candidates = body.get("candidates")
    if not isinstance(candidates, list) or len(candidates) == 0:
        return None
    first = candidates[0]
    if not isinstance(first, dict):
        return None
    content = first.get("content")
    if not isinstance(content, dict):
        return None
    parts = content.get("parts")
    if not isinstance(parts, list) or len(parts) == 0:
        return None
    part = parts[0]
    if not isinstance(part, dict):
        return None
    text = part.get("text")
    return str(text) if isinstance(text, str) else None


def _is_valid_insights_response(value: Any) -> bool:
    """Validate that a parsed response matches the expected schema."""
    if not isinstance(value, dict):
        return False
    return (
        isinstance(value.get("healthScore"), (int, float))
        and isinstance(value.get("grade"), str)
        and isinstance(value.get("insights"), list)
        and isinstance(value.get("summary"), str)
    )


async def call_gemini(
    api_key: str,
    system_prompt: str,
    user_prompt: str,
) -> GeminiInsightsResponse:
    """Call the Gemini API and return a parsed GeminiInsightsResponse.

    Args:
        api_key: The Gemini API key.
        system_prompt: The system-level prompt with instructions.
        user_prompt: The user-level prompt with data.

    Returns:
        A validated GeminiInsightsResponse instance.

    Raises:
        GeminiError: On any API error, timeout, or schema mismatch.
    """
    import json

    timeout = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)

    request_body = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": system_prompt + "\n\n" + user_prompt}],
            }
        ],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.3,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                _API_URL,
                json=request_body,
                headers={
                    "Content-Type": "application/json",
                    # Use header instead of URL query string to avoid key leakage in logs
                    "x-goog-api-key": api_key,
                },
            )
    except httpx.TimeoutException as e:
        raise GeminiError("Request timed out after 30 seconds") from e
    except httpx.RequestError as e:
        raise GeminiError(str(e)) from e

    if response.status_code == 429:
        raise GeminiError(
            "Rate limit exceeded. Please wait a moment and try again.", 429
        )
    if response.status_code in (401, 403):
        raise GeminiError(
            "Invalid or unauthorized API key. Check your Gemini API key.",
            response.status_code,
        )
    if not response.is_success:
        body_text = response.text[:300]
        raise GeminiError(
            f"Gemini API error: HTTP {response.status_code} — {body_text}",
            response.status_code,
        )

    try:
        body = response.json()
    except Exception as e:
        raise GeminiError("Failed to parse Gemini response as JSON") from e

    text = _extract_response_text(body)
    if text is None:
        raise GeminiError("Unexpected response structure from Gemini API")

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        raise GeminiError("Failed to parse Gemini response as JSON") from e

    # Runtime validation — LLM responses may not match the declared schema
    if not _is_valid_insights_response(parsed):
        raise GeminiError("Gemini response did not match expected schema")

    return GeminiInsightsResponse(
        health_score=parsed["healthScore"],
        grade=parsed["grade"],
        insights=parsed["insights"],
        summary=parsed["summary"],
    )
