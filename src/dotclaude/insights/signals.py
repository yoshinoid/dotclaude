"""Rule-based signal detection engine.

Each rule inspects DotClaudeData and emits an InsightSignal when a threshold is crossed.
All arithmetic guards against division-by-zero.
"""

from __future__ import annotations

from dotclaude.models import DotClaudeData, InsightSignal

# Stack-extension to expected rule file mapping
_STACK_RULE_MAP: dict[str, str] = {
    ".py": "backend/python.md",
    ".ts": "frontend/typescript.md",
    ".tsx": "frontend/typescript.md",
    ".go": "backend/golang.md",
    ".java": "backend/java-spring.md",
    ".kt": "mobile/android-kotlin.md",
    ".swift": "mobile/swift.md",
    ".dart": "mobile/flutter.md",
    ".vue": "frontend/vue.md",
}


def detect_signals(data: DotClaudeData) -> list[InsightSignal]:
    """Detect rule-based insight signals from DotClaudeData.

    Returns a list of InsightSignal instances for each rule that fires.
    Returns an empty list when all metrics are healthy.
    """
    signals: list[InsightSignal] = []

    # Rule 1 — Cache hit rate
    # Only fire when enough tokens exist to make the metric meaningful
    if data.cache_stats.total_input_tokens > 1000 and data.cache_stats.hit_rate < 0.5:
        signals.append(
            InsightSignal(
                rule="cacheHitRate",
                severity="warning",
                value=data.cache_stats.hit_rate,
                threshold=0.5,
            )
        )

    # Rule 2 — Agent usage ratio
    total_prompts = data.summary.total_prompts
    if total_prompts > 0:
        agent_ratio = data.subagent_stats.total_runs / total_prompts
        if agent_ratio < 0.05:
            signals.append(
                InsightSignal(
                    rule="agentUsage",
                    severity="info",
                    value=agent_ratio,
                    threshold=0.05,
                )
            )

    # Rule 3 — No hooks configured
    if data.config_status.hooks.total_hooks == 0:
        signals.append(InsightSignal(rule="hooks", severity="error", value=0))

    # Rule 4 — Insufficient rules files
    if data.config_status.rules.count < 3:
        signals.append(
            InsightSignal(
                rule="rules",
                severity="warning",
                value=float(data.config_status.rules.count),
                threshold=3,
            )
        )

    # Rule 5 — Bash overuse relative to Glob/Grep
    # Only fire when there's enough data (bash > 50) to avoid false positives
    bash_count = data.tool_usage.get("Bash", 0)
    glob_count = data.tool_usage.get("Glob", 0)
    grep_count = data.tool_usage.get("Grep", 0)
    search_tool_count = glob_count + grep_count

    if bash_count > 50:
        if search_tool_count == 0:
            signals.append(InsightSignal(rule="bashOveruse", severity="info", value=float(bash_count)))
        elif bash_count / search_tool_count > 10:
            signals.append(
                InsightSignal(
                    rule="bashOveruse",
                    severity="warning",
                    value=round(bash_count / search_tool_count),
                    threshold=10,
                )
            )

    # Rule 6 — No custom commands
    if data.config_status.commands.count == 0:
        signals.append(InsightSignal(rule="commands", severity="info", value=0))

    # Rule 7 — No skills configured
    if data.config_status.skills.count == 0:
        signals.append(InsightSignal(rule="skills", severity="info", value=0))

    # Rule 8 — No MCP servers
    if data.config_status.mcp_servers.count == 0:
        signals.append(InsightSignal(rule="mcp", severity="info", value=0))

    # Rule 9 — Missing stack-specific rules based on file activity
    if data.file_activity is not None:
        rule_files: set[str] = set(data.config_status.rules.files or [])
        ext_entries = sorted(
            data.file_activity.by_extension.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        # Only check top extensions with meaningful usage (>= 10 file operations)
        for ext, count in ext_entries:
            if count < 10:
                break
            expected_rule = _STACK_RULE_MAP.get(ext)
            if expected_rule is not None and expected_rule not in rule_files:
                signals.append(
                    InsightSignal(
                        rule="missingStackRule",
                        severity="info",
                        value=float(count),
                        threshold=10,
                    )
                )
                break  # Only report once — the most impactful missing rule

    return signals
