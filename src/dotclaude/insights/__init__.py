"""Insights package — rule-based signals, recommendations, and Gemini AI analysis."""

from __future__ import annotations

from dotclaude.insights.anonymize import GeminiPayload, build_gemini_payload
from dotclaude.insights.config_store import (
    get_config_file_path,
    get_gemini_api_key,
    get_server_url,
    read_config,
    write_config,
)
from dotclaude.insights.gemini import GeminiError, call_gemini
from dotclaude.insights.locale import detect_locale
from dotclaude.insights.prompts import build_user_prompt, get_system_prompt
from dotclaude.insights.recommendations import generate_recommendations
from dotclaude.insights.signals import detect_signals

__all__ = [
    # signals
    "detect_signals",
    # recommendations
    "generate_recommendations",
    # anonymize
    "GeminiPayload",
    "build_gemini_payload",
    # gemini
    "GeminiError",
    "call_gemini",
    # prompts
    "get_system_prompt",
    "build_user_prompt",
    # locale
    "detect_locale",
    # config store
    "read_config",
    "write_config",
    "get_gemini_api_key",
    "get_config_file_path",
    "get_server_url",
]
