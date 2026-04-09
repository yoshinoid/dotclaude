"""Anonymize DotClaudeData for Gemini API transmission.

NEVER includes: file paths, project names, message content, config names.
ONLY includes: numeric stats and signal data.
"""

from __future__ import annotations

import re
from typing import Any

from dotclaude_types.models import DotClaudeData, InsightSignal


class GeminiPayload:
    """Anonymized payload for Gemini API."""

    def __init__(
        self,
        signals: list[InsightSignal],
        stats: dict[str, Any],
        config: dict[str, Any],
    ) -> None:
        self.signals = signals
        self.stats = stats
        self.config = config

    def to_dict(self) -> dict[str, Any]:
        return {
            "signals": [s.model_dump(by_alias=True) for s in self.signals],
            "stats": self.stats,
            "config": self.config,
        }


def build_gemini_payload(data: DotClaudeData, signals: list[InsightSignal]) -> GeminiPayload:
    """Build an anonymized payload for Gemini API.

    Tool names are safe to send (built-in names like "Bash", "Read").
    Guards against any key that looks like a file path to prevent accidental PII leakage.
    """
    total_prompts = data.summary.total_prompts
    agent_ratio = data.subagent_stats.total_runs / total_prompts if total_prompts > 0 else 0.0

    # Filter out keys that look like file paths
    top_tools = [
        name
        for name, _ in sorted(
            data.tool_usage.items(), key=lambda x: x[1], reverse=True
        )
        if "/" not in name and "\\" not in name
    ][:5]

    # Strip full model IDs to short names
    models_used = [
        re.sub(r"-\d{8}$", "", u.model.replace("claude-", ""))
        for u in data.token_usage
    ]

    return GeminiPayload(
        signals=signals,
        stats={
            "cacheHitRate": data.cache_stats.hit_rate,
            "agentRatio": agent_ratio,
            "totalSessions": data.summary.total_sessions,
            "daysActive": data.summary.days_active,
            "topTools": top_tools,
            "modelsUsed": models_used,
        },
        config={
            "agentsCount": data.config_status.agents.count,
            "commandsCount": data.config_status.commands.count,
            "hooksCount": data.config_status.hooks.total_hooks,
            "rulesCount": data.config_status.rules.count,
            "skillsCount": data.config_status.skills.count,
            "mcpCount": data.config_status.mcp_servers.count,
        },
    )
