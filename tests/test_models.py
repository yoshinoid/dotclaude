"""Tests for dotclaude.models — round-trip serialisation, camelCase aliases, optionality."""

from __future__ import annotations

import json

import pytest

from dotclaude_types.models import (
    AgentsStatus,
    AnalyzeOptions,
    CacheCreation,
    CacheStats,
    CatalogDetect,
    CatalogEntry,
    CatalogRecommendation,
    CommandsStatus,
    ConfigStatus,
    ContentBlock,
    CostByDay,
    CostByModel,
    CostEstimate,
    DailyActivity,
    DotClaudeData,
    DotClaudeMeta,
    DotClaudeMetaFilters,
    FileActivity,
    GeminiInsightItem,
    GeminiInsightsResponse,
    HookFrequency,
    HookFrequencyStats,
    HooksStatus,
    InsightSignal,
    McpServersStatus,
    ModelTokenUsage,
    PluginsStatus,
    ProcessStats,
    ProjectBreakdown,
    ProjectConfig,
    ProjectStats,
    RawAssistantMessage,
    RawAssistantRecord,
    RawBlocklist,
    RawBlocklistEntry,
    RawHistoryEntry,
    RawSessionMeta,
    RawSubagentMeta,
    RawUsage,
    RawUserMessage,
    RawUserRecord,
    Recommendation,
    RulesStatus,
    ServerToolUse,
    SessionDurationStats,
    SkillsStatus,
    SubagentStats,
    SummaryStats,
    TopDirectory,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def roundtrip(model_instance):
    """Serialise to camelCase JSON and parse back to the same model type."""
    cls = type(model_instance)
    raw_json = model_instance.model_dump_json(by_alias=True)
    parsed = cls.model_validate_json(raw_json)
    return parsed, json.loads(raw_json)


# ===========================================================================
# 1. RawUsage — basic required fields + optionals
# ===========================================================================


class TestRawUsage:
    def test_required_fields_only(self):
        usage = RawUsage(input_tokens=100, output_tokens=50)
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.cache_creation_input_tokens is None

    def test_camel_case_aliases(self):
        usage = RawUsage(input_tokens=10, output_tokens=5)
        data = json.loads(usage.model_dump_json(by_alias=True))
        assert "inputTokens" in data
        assert "outputTokens" in data
        assert "input_tokens" not in data

    def test_roundtrip_with_nested(self):
        usage = RawUsage(
            input_tokens=200,
            output_tokens=100,
            server_tool_use=ServerToolUse(web_search_requests=3),
            cache_creation=CacheCreation(ephemeral_5m_input_tokens=10),
        )
        parsed, data = roundtrip(usage)
        assert parsed.server_tool_use is not None
        assert parsed.server_tool_use.web_search_requests == 3
        assert "serverToolUse" in data

    def test_parse_from_camel_json(self):
        payload = {"inputTokens": 300, "outputTokens": 150, "serviceTier": "premium"}
        usage = RawUsage.model_validate(payload)
        assert usage.input_tokens == 300
        assert usage.service_tier == "premium"


# ===========================================================================
# 2. ContentBlock — discriminated union / open model
# ===========================================================================


class TestContentBlock:
    def test_text_block(self):
        block = ContentBlock(type="text", text="Hello world")
        assert block.type == "text"
        assert block.text == "Hello world"

    def test_tool_use_block(self):
        block = ContentBlock(type="tool_use", id="tu_1", name="Bash", input={"cmd": "ls"})
        data = json.loads(block.model_dump_json(by_alias=True))
        assert data["type"] == "tool_use"
        assert data["name"] == "Bash"

    def test_unknown_type_extra_fields(self):
        # extra="allow" means unknown keys are preserved
        block = ContentBlock.model_validate({"type": "custom_block", "customField": "value"})
        assert block.type == "custom_block"

    def test_thinking_block_roundtrip(self):
        block = ContentBlock(type="thinking", thinking="I think therefore I am")
        parsed, _ = roundtrip(block)
        assert parsed.thinking == "I think therefore I am"


# ===========================================================================
# 3. SummaryStats — camelCase round-trip
# ===========================================================================


class TestSummaryStats:
    def test_all_fields(self):
        stats = SummaryStats(
            total_sessions=10,
            total_prompts=200,
            total_assistant_messages=180,
            days_active=5,
            first_activity="2024-01-01",
            last_activity="2024-01-05",
        )
        parsed, data = roundtrip(stats)
        assert parsed.total_sessions == 10
        assert "totalSessions" in data
        assert "totalPrompts" in data
        assert "daysActive" in data

    def test_parse_from_camel_keys(self):
        payload = {
            "totalSessions": 42,
            "totalPrompts": 999,
            "totalAssistantMessages": 800,
            "daysActive": 7,
            "firstActivity": "2024-03-01",
            "lastActivity": "2024-03-07",
        }
        stats = SummaryStats.model_validate(payload)
        assert stats.total_sessions == 42
        assert stats.days_active == 7


# ===========================================================================
# 4. ModelTokenUsage
# ===========================================================================


class TestModelTokenUsage:
    def test_roundtrip(self):
        item = ModelTokenUsage(
            model="claude-3-5-sonnet",
            input_tokens=1000,
            output_tokens=500,
            cache_creation_tokens=200,
            cache_read_tokens=150,
        )
        parsed, data = roundtrip(item)
        assert parsed.model == "claude-3-5-sonnet"
        assert "cacheCreationTokens" in data
        assert "cacheReadTokens" in data


# ===========================================================================
# 5. Optional fields — AnalyzeOptions
# ===========================================================================


class TestAnalyzeOptions:
    def test_all_optional(self):
        opts = AnalyzeOptions()
        assert opts.claude_dir is None
        assert opts.since is None
        assert opts.until is None
        assert opts.top is None

    def test_partial_fill(self):
        opts = AnalyzeOptions(since="2024-01-01", top=20)
        _, data = roundtrip(opts)
        assert data["since"] == "2024-01-01"
        assert data["top"] == 20
        assert data["claudeDir"] is None

    def test_camel_key_claude_dir(self):
        opts = AnalyzeOptions(claude_dir="/home/user/.claude")
        data = json.loads(opts.model_dump_json(by_alias=True))
        assert "claudeDir" in data
        assert data["claudeDir"] == "/home/user/.claude"


# ===========================================================================
# 6. RawAssistantRecord — nested + literal types
# ===========================================================================


class TestRawAssistantRecord:
    def _make(self) -> RawAssistantRecord:
        return RawAssistantRecord(
            parent_uuid=None,
            is_sidechain=False,
            type="assistant",
            message=RawAssistantMessage(
                model="claude-opus-4",
                id="msg_01",
                type="message",
                role="assistant",
                content=[ContentBlock(type="text", text="Hello")],
                stop_reason="end_turn",
                usage=RawUsage(input_tokens=10, output_tokens=5),
            ),
            uuid="rec_01",
            timestamp="2024-06-01T00:00:00Z",
            session_id="sess_01",
        )

    def test_roundtrip(self):
        record = self._make()
        parsed, data = roundtrip(record)
        assert parsed.uuid == "rec_01"
        assert parsed.message.role == "assistant"
        assert "isSidechain" in data
        assert "sessionId" in data

    def test_optional_fields_absent(self):
        record = self._make()
        assert record.git_branch is None
        assert record.slug is None
        assert record.cwd is None

    def test_parse_from_camel_json(self):
        raw = self._make()
        json_str = raw.model_dump_json(by_alias=True)
        parsed = RawAssistantRecord.model_validate_json(json_str)
        assert parsed.session_id == "sess_01"
        assert parsed.is_sidechain is False


# ===========================================================================
# 7. RawUserRecord
# ===========================================================================


class TestRawUserRecord:
    def test_string_content(self):
        record = RawUserRecord(
            parent_uuid="parent_01",
            is_sidechain=False,
            type="user",
            message=RawUserMessage(role="user", content="Hello there"),
            uuid="rec_02",
            timestamp="2024-06-01T00:01:00Z",
            session_id="sess_01",
        )
        parsed, data = roundtrip(record)
        assert parsed.message.content == "Hello there"
        assert "parentUuid" in data

    def test_block_content(self):
        record = RawUserRecord(
            parent_uuid=None,
            is_sidechain=False,
            type="user",
            message=RawUserMessage(
                role="user",
                content=[ContentBlock(type="text", text="image attached")],
            ),
            uuid="rec_03",
            timestamp="2024-06-01T00:02:00Z",
            session_id="sess_01",
        )
        assert isinstance(record.message.content, list)


# ===========================================================================
# 8. RawHistoryEntry — all optional
# ===========================================================================


class TestRawHistoryEntry:
    def test_empty(self):
        entry = RawHistoryEntry()
        assert entry.display is None
        assert entry.session_id is None

    def test_roundtrip(self):
        entry = RawHistoryEntry(
            display="git commit",
            timestamp=1700000000.0,
            project="/home/user/myproject",
            session_id="sess_99",
        )
        parsed, data = roundtrip(entry)
        assert parsed.project == "/home/user/myproject"
        assert "sessionId" in data


# ===========================================================================
# 9. RawSessionMeta
# ===========================================================================


class TestRawSessionMeta:
    def test_roundtrip(self):
        meta = RawSessionMeta(
            pid=12345,
            session_id="sess_abc",
            cwd="/home/user/project",
            started_at=1700000000.0,
            kind="chat",
            entrypoint="cli",
        )
        parsed, data = roundtrip(meta)
        assert parsed.pid == 12345
        assert "startedAt" in data
        assert "sessionId" in data


# ===========================================================================
# 10. RawBlocklist + RawBlocklistEntry
# ===========================================================================


class TestRawBlocklist:
    def test_roundtrip(self):
        blocklist = RawBlocklist(
            fetched_at="2024-01-01T00:00:00Z",
            plugins=[
                RawBlocklistEntry(plugin="bad-plugin", reason="malicious"),
                RawBlocklistEntry(added_at="2024-01-01"),
            ],
        )
        parsed, data = roundtrip(blocklist)
        assert parsed.plugins is not None
        assert len(parsed.plugins) == 2
        assert "fetchedAt" in data


# ===========================================================================
# 11. InsightSignal — severity Literal
# ===========================================================================


class TestInsightSignal:
    def test_error_severity(self):
        sig = InsightSignal(rule="high_cost", severity="error", value=150.0, threshold=100.0)
        parsed, data = roundtrip(sig)
        assert parsed.severity == "error"
        assert parsed.threshold == 100.0
        assert "threshold" in data

    def test_info_no_threshold(self):
        sig = InsightSignal(rule="low_usage", severity="info", value=5.0)
        assert sig.threshold is None
        _, data = roundtrip(sig)
        assert data["threshold"] is None

    def test_invalid_severity_raises(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            InsightSignal(rule="x", severity="critical", value=1.0)  # type: ignore[arg-type]


# ===========================================================================
# 12. GeminiInsightsResponse
# ===========================================================================


class TestGeminiInsightsResponse:
    def test_roundtrip(self):
        resp = GeminiInsightsResponse(
            health_score=72.5,
            grade="B",
            insights=[
                GeminiInsightItem(
                    severity="warning",
                    title="High cache miss rate",
                    description="Cache hit rate below 30%.",
                    recommendation="Enable prompt caching.",
                )
            ],
            summary="Usage is moderate with some inefficiencies.",
        )
        parsed, data = roundtrip(resp)
        assert parsed.health_score == 72.5
        assert "healthScore" in data
        assert len(parsed.insights) == 1
        assert parsed.insights[0].title == "High cache miss rate"


# ===========================================================================
# 13. Recommendation — confidence + optional project
# ===========================================================================


class TestRecommendation:
    def test_global_recommendation(self):
        rec = Recommendation(
            catalog_id="python-backend",
            type="rule",
            name="backend/python.md",
            description="Python conventions",
            reason="python stack detected globally",
            confidence="high",
            action_path="/home/user/.claude/rules/backend/python.md",
        )
        assert rec.project is None
        _, data = roundtrip(rec)
        assert "catalogId" in data
        assert "actionPath" in data
        assert data["confidence"] == "high"

    def test_project_scoped_recommendation(self):
        rec = Recommendation(
            catalog_id="react",
            type="agent",
            name="react-specialist",
            description="React specialist",
            reason="/home/user/myapp uses react stack",
            project="/home/user/myapp",
            confidence="medium",
            action_path="/home/user/.claude/agents/react-specialist.md",
        )
        parsed, _ = roundtrip(rec)
        assert parsed.project == "/home/user/myapp"


# ===========================================================================
# 14. CatalogEntry — nested detect + recommendations
# ===========================================================================


class TestCatalogEntry:
    def test_roundtrip(self):
        entry = CatalogEntry(
            id="python-backend",
            detect=CatalogDetect(extensions=[".py"], tech_stack=["python"]),
            recommendations=[
                CatalogRecommendation(
                    type="rule",
                    name="backend/python.md",
                    description="Python coding conventions",
                    rule_file="backend/python.md",
                ),
                CatalogRecommendation(
                    type="agent",
                    name="python-pro",
                    description="Python specialist",
                    agent_name="python-pro",
                ),
            ],
        )
        parsed, data = roundtrip(entry)
        assert parsed.id == "python-backend"
        assert parsed.detect.extensions == [".py"]
        assert "techStack" in data["detect"]
        assert len(parsed.recommendations) == 2
        assert "ruleFile" in data["recommendations"][0]
        assert "agentName" in data["recommendations"][1]


# ===========================================================================
# 15. DotClaudeData — full top-level model (integration)
# ===========================================================================


class TestDotClaudeData:
    def _make(self) -> DotClaudeData:
        return DotClaudeData(
            meta=DotClaudeMeta(
                claude_dir="/home/user/.claude",
                scanned_at="2024-06-01T00:00:00Z",
                version="0.4.0",
                filters=DotClaudeMetaFilters(since="2024-01-01"),
            ),
            summary=SummaryStats(
                total_sessions=5,
                total_prompts=100,
                total_assistant_messages=90,
                days_active=3,
                first_activity="2024-01-01",
                last_activity="2024-01-03",
            ),
            tool_usage={"Bash": 50, "Read": 30},
            token_usage=[
                ModelTokenUsage(
                    model="claude-opus-4",
                    input_tokens=5000,
                    output_tokens=2000,
                    cache_creation_tokens=500,
                    cache_read_tokens=300,
                )
            ],
            cost_estimate=CostEstimate(
                total=1.23,
                by_model=[CostByModel(model="claude-opus-4", cost=1.23)],
                by_day=[CostByDay(date="2024-01-01", cost=0.41)],
            ),
            projects=[
                ProjectStats(
                    encoded_path="home-user-myproject",
                    decoded_path="/home/user/myproject",
                    session_count=3,
                    prompt_count=60,
                    memory_file_count=2,
                    last_activity="2024-01-03",
                )
            ],
            daily_activity=[DailyActivity(date="2024-01-01", prompts=30, sessions=2)],
            process_stats=ProcessStats(by_kind={"chat": 3}, by_entrypoint={"cli": 3}),
            subagent_stats=SubagentStats(total_runs=2, by_type={"bash": 2}),
            config_status=ConfigStatus(
                agents=AgentsStatus(count=2, names=["python-pro", "react-specialist"]),
                commands=CommandsStatus(count=1, names=["deploy"]),
                hooks=HooksStatus(total_hooks=3, by_event={"PreToolUse": 2, "PostToolUse": 1}),
                rules=RulesStatus(count=4, domains=["backend"], files=["backend/python.md"]),
                skills=SkillsStatus(count=1, names=["debugging"]),
                plugins=PluginsStatus(marketplace_count=0, marketplaces=[], blocked_count=0),
                mcp_servers=McpServersStatus(count=1, names=["filesystem"]),
            ),
            session_durations=SessionDurationStats(
                count=5,
                total_seconds=3600.0,
                average_seconds=720.0,
                max_seconds=1800.0,
            ),
            cache_stats=CacheStats(
                cache_read_tokens=300,
                cache_creation_tokens=500,
                total_input_tokens=5000,
                hit_rate=0.056,
            ),
            hook_frequency=HookFrequencyStats(
                total_estimated_runs=120,
                hooks=[
                    HookFrequency(
                        event="PreToolUse",
                        matcher="Bash",
                        command="/home/user/.claude/hooks/check.sh",
                        estimated_runs=50,
                    )
                ],
            ),
            file_activity=FileActivity(
                by_extension={".py": 180, ".ts": 95},
                top_directories=[TopDirectory(path="/home/user/myproject/src", count=120)],
            ),
        )

    def test_full_roundtrip(self):
        data_obj = self._make()
        parsed, data = roundtrip(data_obj)
        # top-level camelCase keys
        assert "toolUsage" in data
        assert "tokenUsage" in data
        assert "costEstimate" in data
        assert "dailyActivity" in data
        assert "processStats" in data
        assert "subagentStats" in data
        assert "configStatus" in data
        assert "sessionDurations" in data
        assert "cacheStats" in data
        assert "hookFrequency" in data
        assert "fileActivity" in data

    def test_nested_camel_keys(self):
        data_obj = self._make()
        _, data = roundtrip(data_obj)
        assert "claudeDir" in data["meta"]
        assert "scannedAt" in data["meta"]
        assert "totalSessions" in data["summary"]
        assert "byExtension" in data["fileActivity"]
        assert "topDirectories" in data["fileActivity"]
        assert "totalHooks" in data["configStatus"]["hooks"]

    def test_file_activity_optional_defaults_none(self):
        data_obj = self._make()
        data_obj.file_activity = None
        _, data = roundtrip(data_obj)
        assert data["fileActivity"] is None

    def test_snake_case_access_after_camel_parse(self):
        data_obj = self._make()
        json_str = data_obj.model_dump_json(by_alias=True)
        # Parse via camelCase JSON — Python attributes should still be snake_case
        parsed = DotClaudeData.model_validate_json(json_str)
        assert parsed.tool_usage["Bash"] == 50
        assert parsed.config_status.hooks.total_hooks == 3
        assert parsed.hook_frequency.total_estimated_runs == 120

    def test_project_stats_optional_fields(self):
        data_obj = self._make()
        project = data_obj.projects[0]
        assert project.breakdown is None
        assert project.tech_stack is None
        assert project.project_config is None

    def test_project_config_roundtrip(self):
        config = ProjectConfig(
            has_claude_dir=True,
            has_claude_md=True,
            agents=["python-pro"],
            rules=["backend/python.md"],
            hook_count=2,
            claude_md_keywords=["python", "fastapi"],
        )
        parsed, data = roundtrip(config)
        assert "hasClaudeDir" in data
        assert "hasClaudeMd" in data
        assert "claudeMdKeywords" in data
        assert parsed.claude_md_keywords == ["python", "fastapi"]

    def test_project_breakdown_roundtrip(self):
        breakdown = ProjectBreakdown(
            tool_usage={"Bash": 10},
            file_extensions={".py": 50},
            agent_usage={"python-pro": 3},
            model_usage={"claude-opus-4": 20},
        )
        parsed, data = roundtrip(breakdown)
        assert "toolUsage" in data
        assert "fileExtensions" in data
        assert "agentUsage" in data
        assert "modelUsage" in data
        assert parsed.file_extensions[".py"] == 50

    def test_subagent_meta_roundtrip(self):
        meta = RawSubagentMeta(agent_type="orchestrator", description="Main agent")
        parsed, data = roundtrip(meta)
        assert "agentType" in data
        assert parsed.agent_type == "orchestrator"
