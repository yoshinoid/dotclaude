"""Tests for the rule-based signal detection engine.

Ported from TypeScript: src/__tests__/insights/signals.test.ts
"""

from __future__ import annotations

from dotclaude.insights.signals import detect_signals
from dotclaude.models import DotClaudeData


def _make_data(**overrides: object) -> DotClaudeData:
    base: dict[str, object] = {
        "meta": {"claude_dir": "/tmp", "scanned_at": "", "version": "0.2.0"},
        "summary": {
            "total_sessions": 10,
            "total_prompts": 100,
            "total_assistant_messages": 90,
            "days_active": 5,
            "first_activity": "",
            "last_activity": "",
        },
        "tool_usage": {"Bash": 5, "Glob": 10, "Grep": 5},
        "token_usage": [],
        "cost_estimate": {"total": 1, "by_model": [], "by_day": []},
        "projects": [],
        "daily_activity": [],
        "process_stats": {"by_kind": {}, "by_entrypoint": {}},
        "subagent_stats": {"total_runs": 10, "by_type": {}},
        "config_status": {
            "agents": {"count": 3, "names": []},
            "commands": {"count": 3, "names": []},
            "hooks": {"total_hooks": 5, "by_event": {}},
            "rules": {"count": 5, "domains": [], "files": []},
            "skills": {"count": 2, "names": []},
            "plugins": {"marketplace_count": 0, "marketplaces": [], "blocked_count": 0},
            "mcp_servers": {"count": 2, "names": []},
        },
        "session_durations": {
            "count": 5,
            "total_seconds": 3600,
            "average_seconds": 720,
            "max_seconds": 1800,
        },
        "cache_stats": {
            "cache_read_tokens": 8000,
            "cache_creation_tokens": 2000,
            "total_input_tokens": 10000,
            "hit_rate": 0.8,
        },
        "hook_frequency": {"total_estimated_runs": 0, "hooks": []},
    }
    base.update(overrides)
    return DotClaudeData.model_validate(base)


class TestNoSignalsOnHealthyData:
    def test_returns_empty_array_when_all_metrics_are_healthy(self) -> None:
        data = _make_data()
        assert detect_signals(data) == []


class TestCacheHitRate:
    def test_fires_when_hit_rate_is_below_0_5_with_sufficient_tokens(self) -> None:
        data = _make_data(
            cache_stats={
                "cache_read_tokens": 300,
                "cache_creation_tokens": 700,
                "total_input_tokens": 2000,
                "hit_rate": 0.15,
            }
        )
        signals = detect_signals(data)
        assert any(s.rule == "cacheHitRate" for s in signals)

    def test_does_not_fire_when_tokens_are_too_few(self) -> None:
        data = _make_data(
            cache_stats={
                "cache_read_tokens": 10,
                "cache_creation_tokens": 10,
                "total_input_tokens": 20,
                "hit_rate": 0.1,
            }
        )
        assert not any(s.rule == "cacheHitRate" for s in detect_signals(data))

    def test_does_not_fire_when_hit_rate_is_0_5_or_above(self) -> None:
        data = _make_data(
            cache_stats={
                "cache_read_tokens": 5000,
                "cache_creation_tokens": 5000,
                "total_input_tokens": 10000,
                "hit_rate": 0.5,
            }
        )
        assert not any(s.rule == "cacheHitRate" for s in detect_signals(data))


class TestAgentUsage:
    def test_fires_when_agent_ratio_is_below_0_05(self) -> None:
        base = _make_data()
        data = _make_data(
            summary={**base.summary.model_dump(), "total_prompts": 200},
            subagent_stats={"total_runs": 1, "by_type": {}},
        )
        assert any(s.rule == "agentUsage" for s in detect_signals(data))

    def test_does_not_fire_when_total_prompts_is_0(self) -> None:
        base = _make_data()
        data = _make_data(
            summary={**base.summary.model_dump(), "total_prompts": 0},
            subagent_stats={"total_runs": 0, "by_type": {}},
        )
        assert not any(s.rule == "agentUsage" for s in detect_signals(data))


class TestHooks:
    def test_fires_with_error_severity_when_no_hooks(self) -> None:
        base = _make_data()
        data = _make_data(
            config_status={
                **base.config_status.model_dump(),
                "hooks": {"total_hooks": 0, "by_event": {}},
            }
        )
        signals = detect_signals(data)
        signal = next((s for s in signals if s.rule == "hooks"), None)
        assert signal is not None
        assert signal.severity == "error"

    def test_does_not_fire_when_hooks_are_configured(self) -> None:
        assert not any(s.rule == "hooks" for s in detect_signals(_make_data()))


class TestRules:
    def test_fires_when_rules_count_is_below_3(self) -> None:
        base = _make_data()
        data = _make_data(
            config_status={
                **base.config_status.model_dump(),
                "rules": {"count": 1, "domains": [], "files": []},
            }
        )
        assert any(s.rule == "rules" for s in detect_signals(data))

    def test_does_not_fire_when_rules_count_is_3_or_more(self) -> None:
        assert not any(s.rule == "rules" for s in detect_signals(_make_data()))


class TestBashOveruse:
    def test_fires_warning_when_bash_search_ratio_exceeds_10(self) -> None:
        data = _make_data(tool_usage={"Bash": 110, "Glob": 5, "Grep": 5})
        signal = next(
            (s for s in detect_signals(data) if s.rule == "bashOveruse"), None
        )
        assert signal is not None
        assert signal.severity == "warning"

    def test_fires_info_when_bash_above_50_and_no_search_tools(self) -> None:
        data = _make_data(tool_usage={"Bash": 60})
        signal = next(
            (s for s in detect_signals(data) if s.rule == "bashOveruse"), None
        )
        assert signal is not None
        assert signal.severity == "info"

    def test_does_not_fire_when_bash_count_is_50_or_below(self) -> None:
        data = _make_data(tool_usage={"Bash": 50})
        assert not any(s.rule == "bashOveruse" for s in detect_signals(data))


class TestConfigItems:
    def test_fires_for_commands_skills_mcp_when_all_zero(self) -> None:
        base = _make_data()
        data = _make_data(
            config_status={
                **base.config_status.model_dump(),
                "commands": {"count": 0, "names": []},
                "skills": {"count": 0, "names": []},
                "mcp_servers": {"count": 0, "names": []},
            }
        )
        rules = [s.rule for s in detect_signals(data)]
        assert "commands" in rules
        assert "skills" in rules
        assert "mcp" in rules


class TestMissingStackRule:
    def test_fires_when_top_file_extension_has_no_matching_rule(self) -> None:
        base = _make_data()
        data = _make_data(
            file_activity={
                "by_extension": {".py": 50, ".md": 5},
                "top_directories": [],
            },
            config_status={
                **base.config_status.model_dump(),
                "rules": {
                    "count": 3,
                    "domains": ["frontend"],
                    "files": ["frontend/typescript.md"],
                },
            },
        )
        assert any(s.rule == "missingStackRule" for s in detect_signals(data))

    def test_does_not_fire_when_matching_rule_exists(self) -> None:
        base = _make_data()
        data = _make_data(
            file_activity={
                "by_extension": {".py": 50},
                "top_directories": [],
            },
            config_status={
                **base.config_status.model_dump(),
                "rules": {
                    "count": 5,
                    "domains": ["backend"],
                    "files": ["backend/python.md"],
                },
            },
        )
        assert not any(s.rule == "missingStackRule" for s in detect_signals(data))

    def test_does_not_fire_when_file_activity_count_is_below_threshold(self) -> None:
        data = _make_data(
            file_activity={"by_extension": {".py": 5}, "top_directories": []}
        )
        assert not any(s.rule == "missingStackRule" for s in detect_signals(data))

    def test_does_not_fire_when_no_file_activity(self) -> None:
        assert not any(
            s.rule == "missingStackRule" for s in detect_signals(_make_data())
        )
