"""
Pydantic v2 models ported from the TypeScript source.

Mirrors:
  - src/parser/types.ts      (raw JSONL records, session/plugin/subagent meta, output types)
  - src/insights/types.ts    (InsightSignal, GeminiInsightItem, GeminiInsightsResponse)
  - src/insights/recommendations.ts (CatalogEntry, CatalogRecommendation, Recommendation)

All models use alias_generator=to_camel so JSON serialisation matches the
camelCase keys produced by the TypeScript server.  Python code uses
snake_case attribute names throughout.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

# ---------------------------------------------------------------------------
# Shared config factory
# ---------------------------------------------------------------------------

_CAMEL = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ===========================================================================
# Raw JSONL record types
# ===========================================================================


class ServerToolUse(BaseModel):
    model_config = _CAMEL

    web_search_requests: int | None = None
    web_fetch_requests: int | None = None


class CacheCreation(BaseModel):
    model_config = _CAMEL

    ephemeral_5m_input_tokens: int | None = None
    ephemeral_1h_input_tokens: int | None = None


class RawUsage(BaseModel):
    model_config = _CAMEL

    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int | None = None
    cache_read_input_tokens: int | None = None
    service_tier: str | None = None
    server_tool_use: ServerToolUse | None = None
    cache_creation: CacheCreation | None = None
    inference_geo: str | None = None
    # iterations is unknown[] in TS — kept as a list of arbitrary values
    iterations: list[Any] | None = None
    speed: str | None = None


# ContentBlock is a TS discriminated union.  We represent it as a flexible
# model that accepts any extra fields (open model) and provides typed access
# to the common discriminator and the most frequently used fields.
class ContentBlock(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="allow",
    )

    type: str
    # text variant
    text: str | None = None
    # tool_use variant
    id: str | None = None
    name: str | None = None
    input: Any | None = None
    caller: Any | None = None
    # thinking variant
    thinking: str | None = None
    signature: str | None = None


class RawAssistantMessage(BaseModel):
    model_config = _CAMEL

    model: str
    id: str
    type: Literal["message"]
    role: Literal["assistant"]
    content: list[ContentBlock]
    stop_reason: Literal["end_turn", "tool_use"] | None
    usage: RawUsage


class RawUserMessage(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="allow",
    )

    role: Literal["user"]
    # content is string | ContentBlock[] in TS
    content: str | list[ContentBlock]


class RawAssistantRecord(BaseModel):
    model_config = _CAMEL

    parent_uuid: str | None
    is_sidechain: bool
    type: Literal["assistant"]
    message: RawAssistantMessage
    uuid: str
    timestamp: str
    user_type: str | None = None
    entrypoint: str | None = None
    cwd: str | None = None
    session_id: str
    version: str | None = None
    git_branch: str | None = None
    slug: str | None = None


class RawUserRecord(BaseModel):
    model_config = _CAMEL

    parent_uuid: str | None
    is_sidechain: bool
    type: Literal["user"]
    message: RawUserMessage
    uuid: str
    timestamp: str
    permission_mode: str | None = None
    user_type: str | None = None
    entrypoint: str | None = None
    cwd: str | None = None
    session_id: str
    version: str | None = None
    git_branch: str | None = None


class RawUnknownRecord(BaseModel):
    """Records we skip (permission-mode, file-history-snapshot, attachment, etc.)"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="allow",
    )

    type: str


# ===========================================================================
# history.jsonl
# ===========================================================================


class RawHistoryEntry(BaseModel):
    model_config = _CAMEL

    display: str | None = None
    pasted_contents: dict[str, Any] | None = None
    timestamp: float | None = None
    project: str | None = None
    session_id: str | None = None


# ===========================================================================
# sessions/*.json
# ===========================================================================


class RawSessionMeta(BaseModel):
    model_config = _CAMEL

    pid: int | None = None
    session_id: str | None = None
    cwd: str | None = None
    started_at: float | None = None
    kind: str | None = None
    entrypoint: str | None = None


# ===========================================================================
# plugins/blocklist.json
# ===========================================================================


class RawBlocklistEntry(BaseModel):
    model_config = _CAMEL

    plugin: str | None = None
    added_at: str | None = None
    reason: str | None = None
    text: str | None = None


class RawBlocklist(BaseModel):
    model_config = _CAMEL

    fetched_at: str | None = None
    plugins: list[RawBlocklistEntry] | None = None


# ===========================================================================
# plugins/known_marketplaces.json
# ===========================================================================


class RawMarketplace(BaseModel):
    model_config = _CAMEL

    source: Any | None = None
    install_location: str | None = None
    last_updated: str | None = None


# ===========================================================================
# subagent .meta.json
# ===========================================================================


class RawSubagentMeta(BaseModel):
    model_config = _CAMEL

    agent_type: str | None = None
    description: str | None = None


# ===========================================================================
# Analyze options
# ===========================================================================


class AnalyzeOptions(BaseModel):
    model_config = _CAMEL

    # Custom path to ~/.claude directory
    claude_dir: str | None = None
    # Include only records on or after this date (YYYY-MM-DD)
    since: str | None = None
    # Include only records on or before this date (YYYY-MM-DD)
    until: str | None = None
    # Max items per section in the dashboard (default: no limit)
    top: int | None = None


# ===========================================================================
# Scan manifest
# ===========================================================================


class ScanManifest(BaseModel):
    model_config = _CAMEL

    claude_dir: str
    scanned_at: str
    version: str
    filters: dict[str, str | None] | None = None


# ===========================================================================
# Output types
# ===========================================================================


class SummaryStats(BaseModel):
    model_config = _CAMEL

    total_sessions: int
    total_prompts: int
    total_assistant_messages: int
    days_active: int
    first_activity: str
    last_activity: str


class ModelTokenUsage(BaseModel):
    model_config = _CAMEL

    model: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int


class CostByModel(BaseModel):
    model_config = _CAMEL

    model: str
    cost: float


class CostByDay(BaseModel):
    model_config = _CAMEL

    date: str
    cost: float


class CostEstimate(BaseModel):
    model_config = _CAMEL

    total: float
    by_model: list[CostByModel]
    by_day: list[CostByDay]


class ProjectBreakdown(BaseModel):
    model_config = _CAMEL

    tool_usage: dict[str, int]
    file_extensions: dict[str, int]
    agent_usage: dict[str, int]
    model_usage: dict[str, int]


class ProjectConfig(BaseModel):
    """Project-level .claude/ config detected at the actual project directory."""

    model_config = _CAMEL

    # Has a .claude/ directory
    has_claude_dir: bool
    # Has CLAUDE.md at project root or .claude/CLAUDE.md
    has_claude_md: bool
    # Agent names found in project .claude/agents/
    agents: list[str]
    # Rule relative paths found in project .claude/rules/
    rules: list[str]
    # Hook count in project .claude/settings.json or hooks/
    hook_count: int
    # Keywords detected in CLAUDE.md content (tech stack hints)
    claude_md_keywords: list[str]


class ProjectStats(BaseModel):
    model_config = _CAMEL

    encoded_path: str
    decoded_path: str
    session_count: int
    prompt_count: int
    memory_file_count: int
    last_activity: str
    # Per-project usage breakdown from conversation cwd data
    breakdown: ProjectBreakdown | None = None
    # Detected tech stack from manifest files (package.json, pyproject.toml, etc.)
    tech_stack: list[str] | None = None
    # Project-level .claude/ config (agents, rules, hooks found locally)
    project_config: ProjectConfig | None = None


class DailyActivity(BaseModel):
    model_config = _CAMEL

    date: str
    prompts: int
    sessions: int


class ProcessStats(BaseModel):
    model_config = _CAMEL

    by_kind: dict[str, int]
    by_entrypoint: dict[str, int]


class SubagentStats(BaseModel):
    model_config = _CAMEL

    total_runs: int
    by_type: dict[str, int]


class AgentsStatus(BaseModel):
    model_config = _CAMEL

    count: int
    names: list[str]


class CommandsStatus(BaseModel):
    model_config = _CAMEL

    count: int
    names: list[str]


class HooksStatus(BaseModel):
    model_config = _CAMEL

    total_hooks: int
    by_event: dict[str, int]


class RulesStatus(BaseModel):
    model_config = _CAMEL

    count: int
    domains: list[str]
    files: list[str]


class SkillsStatus(BaseModel):
    model_config = _CAMEL

    count: int
    names: list[str]


class PluginsStatus(BaseModel):
    model_config = _CAMEL

    marketplace_count: int
    marketplaces: list[str]
    blocked_count: int


class McpServersStatus(BaseModel):
    model_config = _CAMEL

    count: int
    names: list[str]


class ConfigStatus(BaseModel):
    model_config = _CAMEL

    agents: AgentsStatus
    commands: CommandsStatus
    hooks: HooksStatus
    rules: RulesStatus
    skills: SkillsStatus
    plugins: PluginsStatus
    mcp_servers: McpServersStatus


class HookFrequency(BaseModel):
    model_config = _CAMEL

    # Event name (e.g., PreToolUse, PostToolUse, SessionStart)
    event: str
    # Matcher pattern (e.g., "Bash", "Write|Edit|MultiEdit", "" for all)
    matcher: str
    # Command or script path
    command: str
    # Estimated execution count based on tool usage / session data
    estimated_runs: int


class HookFrequencyStats(BaseModel):
    model_config = _CAMEL

    # Total estimated hook executions across all hooks
    total_estimated_runs: int
    # Per-hook frequency details
    hooks: list[HookFrequency]


class SessionDurationStats(BaseModel):
    model_config = _CAMEL

    # Total sessions with computable duration
    count: int
    # Total duration in seconds across all sessions
    total_seconds: float
    # Average session duration in seconds
    average_seconds: float
    # Longest session duration in seconds
    max_seconds: float


class CacheStats(BaseModel):
    model_config = _CAMEL

    # Total cache read tokens
    cache_read_tokens: int
    # Total cache creation tokens
    cache_creation_tokens: int
    # Total input tokens (non-cache)
    total_input_tokens: int
    # Cache hit rate: cacheRead / (cacheRead + totalInput)
    hit_rate: float


class TopDirectory(BaseModel):
    model_config = _CAMEL

    path: str
    count: int


class FileActivity(BaseModel):
    model_config = _CAMEL

    # File extension → edit/read count (e.g., ".py": 180, ".ts": 95)
    by_extension: dict[str, int]
    # Top directories by file operation count
    top_directories: list[TopDirectory]


class DotClaudeMetaFilters(BaseModel):
    model_config = _CAMEL

    since: str | None = None
    until: str | None = None


class DotClaudeMeta(BaseModel):
    model_config = _CAMEL

    claude_dir: str
    scanned_at: str
    version: str
    filters: DotClaudeMetaFilters | None = None


class DotClaudeData(BaseModel):
    model_config = _CAMEL

    meta: DotClaudeMeta
    summary: SummaryStats
    tool_usage: dict[str, int]
    token_usage: list[ModelTokenUsage]
    cost_estimate: CostEstimate
    projects: list[ProjectStats]
    daily_activity: list[DailyActivity]
    process_stats: ProcessStats
    subagent_stats: SubagentStats
    config_status: ConfigStatus
    # Session durations in seconds, keyed by sessionId
    session_durations: SessionDurationStats
    # Cache hit rate across all models
    cache_stats: CacheStats
    # Estimated hook execution frequency
    hook_frequency: HookFrequencyStats
    # File extension distribution from tool_use file paths
    file_activity: FileActivity | None = None


# ===========================================================================
# Insight types  (src/insights/types.ts)
# ===========================================================================

InsightSeverity = Literal["error", "warning", "info"]


class InsightSignal(BaseModel):
    model_config = _CAMEL

    # Rule identifier
    rule: str
    severity: InsightSeverity
    # Observed value that triggered the signal
    value: float
    # Threshold that was crossed (if applicable)
    threshold: float | None = None


class GeminiInsightItem(BaseModel):
    model_config = _CAMEL

    severity: InsightSeverity
    title: str
    description: str
    recommendation: str


class GeminiInsightsResponse(BaseModel):
    model_config = _CAMEL

    health_score: float
    grade: str
    insights: list[GeminiInsightItem]
    summary: str


# ===========================================================================
# Recommendation types  (src/insights/recommendations.ts)
# ===========================================================================

RecommendationType = Literal["agent", "rule", "hook", "skill"]
RecommendationConfidence = Literal["high", "medium", "low"]


class CatalogDetect(BaseModel):
    model_config = _CAMEL

    extensions: list[str] | None = None
    tech_stack: list[str] | None = None


class CatalogRecommendation(BaseModel):
    model_config = _CAMEL

    type: RecommendationType
    name: str
    description: str
    # Rule file path to check (e.g., "backend/python.md")
    rule_file: str | None = None
    # Agent name to check in config
    agent_name: str | None = None


class CatalogEntry(BaseModel):
    model_config = _CAMEL

    id: str
    detect: CatalogDetect
    recommendations: list[CatalogRecommendation]


class Recommendation(BaseModel):
    model_config = _CAMEL

    # Which catalog entry produced this
    catalog_id: str
    type: RecommendationType
    name: str
    description: str
    # Why this is recommended
    reason: str
    # Which project triggered this (None = global)
    project: str | None = None
    confidence: RecommendationConfidence
    # Full path where the config file should be created
    action_path: str


# ---------------------------------------------------------------------------
# Convenience re-exports — single import surface
# ---------------------------------------------------------------------------

__all__ = [
    # raw records
    "ServerToolUse",
    "CacheCreation",
    "RawUsage",
    "ContentBlock",
    "RawAssistantMessage",
    "RawUserMessage",
    "RawAssistantRecord",
    "RawUserRecord",
    "RawUnknownRecord",
    # history
    "RawHistoryEntry",
    # session
    "RawSessionMeta",
    # plugins
    "RawBlocklistEntry",
    "RawBlocklist",
    "RawMarketplace",
    # subagent
    "RawSubagentMeta",
    # options / manifest
    "AnalyzeOptions",
    "ScanManifest",
    # output types
    "SummaryStats",
    "ModelTokenUsage",
    "CostByModel",
    "CostByDay",
    "CostEstimate",
    "ProjectBreakdown",
    "ProjectConfig",
    "ProjectStats",
    "DailyActivity",
    "ProcessStats",
    "SubagentStats",
    "AgentsStatus",
    "CommandsStatus",
    "HooksStatus",
    "RulesStatus",
    "SkillsStatus",
    "PluginsStatus",
    "McpServersStatus",
    "ConfigStatus",
    "HookFrequency",
    "HookFrequencyStats",
    "SessionDurationStats",
    "CacheStats",
    "TopDirectory",
    "FileActivity",
    "DotClaudeMetaFilters",
    "DotClaudeMeta",
    "DotClaudeData",
    # insights
    "InsightSeverity",
    "InsightSignal",
    "GeminiInsightItem",
    "GeminiInsightsResponse",
    # recommendations
    "RecommendationType",
    "RecommendationConfidence",
    "CatalogDetect",
    "CatalogRecommendation",
    "CatalogEntry",
    "Recommendation",
]
