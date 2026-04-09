"""Tests for the config evolution recommendation engine.

Ported from TypeScript: src/__tests__/insights/recommendations.test.ts
"""

from __future__ import annotations

from dotclaude_types.models import DotClaudeData

from dotclaude.insights.recommendations import generate_recommendations


def _make_data(**overrides: object) -> DotClaudeData:
    base: dict[str, object] = {
        "meta": {"claude_dir": "/tmp", "scanned_at": "", "version": "0.3.0"},
        "summary": {
            "total_sessions": 10,
            "total_prompts": 100,
            "total_assistant_messages": 90,
            "days_active": 5,
            "first_activity": "",
            "last_activity": "",
        },
        "tool_usage": {},
        "token_usage": [],
        "cost_estimate": {"total": 1, "by_model": [], "by_day": []},
        "projects": [],
        "daily_activity": [],
        "process_stats": {"by_kind": {}, "by_entrypoint": {}},
        "subagent_stats": {"total_runs": 10, "by_type": {}},
        "config_status": {
            "agents": {"count": 0, "names": []},
            "commands": {"count": 3, "names": []},
            "hooks": {"total_hooks": 5, "by_event": {}},
            "rules": {"count": 0, "domains": [], "files": []},
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


class TestGenerateRecommendations:
    def test_recommends_python_rules_and_agents_for_python_projects(self) -> None:
        data = _make_data(
            projects=[
                {
                    "encoded_path": "test",
                    "decoded_path": "/projects/myapp",
                    "session_count": 5,
                    "prompt_count": 50,
                    "memory_file_count": 1,
                    "last_activity": "",
                    "tech_stack": ["python"],
                    "breakdown": {
                        "tool_usage": {"Write": 20, "Edit": 30},
                        "file_extensions": {".py": 40},
                        "agent_usage": {},
                        "model_usage": {},
                    },
                }
            ]
        )

        recs = generate_recommendations(data)
        assert len(recs) > 0

        rule_rec = next((r for r in recs if r.name == "backend/python.md"), None)
        assert rule_rec is not None
        assert "rules/backend/python.md" in rule_rec.action_path

        agent_rec = next((r for r in recs if r.name == "python-pro"), None)
        assert agent_rec is not None
        assert "agents/python-pro.md" in agent_rec.action_path

    def test_skips_recommendations_for_already_configured_items(self) -> None:
        data = _make_data(
            config_status={
                "agents": {"count": 1, "names": ["python-pro"]},
                "commands": {"count": 0, "names": []},
                "hooks": {"total_hooks": 0, "by_event": {}},
                "rules": {"count": 1, "domains": ["backend"], "files": ["backend/python.md"]},
                "skills": {"count": 0, "names": []},
                "plugins": {"marketplace_count": 0, "marketplaces": [], "blocked_count": 0},
                "mcp_servers": {"count": 0, "names": []},
            },
            projects=[
                {
                    "encoded_path": "test",
                    "decoded_path": "/projects/myapp",
                    "session_count": 5,
                    "prompt_count": 50,
                    "memory_file_count": 1,
                    "last_activity": "",
                    "tech_stack": ["python"],
                    "breakdown": {
                        "tool_usage": {},
                        "file_extensions": {".py": 40},
                        "agent_usage": {},
                        "model_usage": {},
                    },
                }
            ],
        )

        recs = generate_recommendations(data)
        assert not any(r.name == "backend/python.md" for r in recs)
        assert not any(r.name == "python-pro" for r in recs)

    def test_returns_empty_for_projects_with_no_matching_tech_stack(self) -> None:
        data = _make_data(
            projects=[
                {
                    "encoded_path": "test",
                    "decoded_path": "/projects/docs",
                    "session_count": 5,
                    "prompt_count": 50,
                    "memory_file_count": 1,
                    "last_activity": "",
                    "breakdown": {
                        "tool_usage": {},
                        "file_extensions": {".md": 100},
                        "agent_usage": {},
                        "model_usage": {},
                    },
                }
            ]
        )
        assert generate_recommendations(data) == []

    def test_recommends_typescript_tools_for_tsx_heavy_projects(self) -> None:
        data = _make_data(
            projects=[
                {
                    "encoded_path": "test",
                    "decoded_path": "/projects/web",
                    "session_count": 10,
                    "prompt_count": 100,
                    "memory_file_count": 1,
                    "last_activity": "",
                    "tech_stack": ["node"],
                    "breakdown": {
                        "tool_usage": {},
                        "file_extensions": {".tsx": 60, ".ts": 30},
                        "agent_usage": {},
                        "model_usage": {},
                    },
                }
            ]
        )

        recs = generate_recommendations(data)
        assert any(r.name == "frontend/typescript.md" for r in recs)
        assert any(r.name == "frontend/react.md" for r in recs)

    def test_assigns_high_confidence_for_extensions_above_50(self) -> None:
        data = _make_data(
            projects=[
                {
                    "encoded_path": "test",
                    "decoded_path": "/projects/app",
                    "session_count": 5,
                    "prompt_count": 50,
                    "memory_file_count": 1,
                    "last_activity": "",
                    "breakdown": {
                        "tool_usage": {},
                        "file_extensions": {".go": 80},
                        "agent_usage": {},
                        "model_usage": {},
                    },
                    "tech_stack": ["go"],
                }
            ]
        )

        recs = generate_recommendations(data)
        go_rec = next((r for r in recs if r.name == "backend/golang.md"), None)
        assert go_rec is not None
        assert go_rec.confidence == "high"

    def test_uses_global_file_activity_when_no_project_breakdown(self) -> None:
        data = _make_data(
            file_activity={
                "by_extension": {".dart": 30},
                "top_directories": [],
            },
            projects=[
                {
                    "encoded_path": "test",
                    "decoded_path": "/projects/app",
                    "session_count": 5,
                    "prompt_count": 50,
                    "memory_file_count": 1,
                    "last_activity": "",
                    "tech_stack": ["dart"],
                }
            ],
        )

        recs = generate_recommendations(data)
        assert any(r.name == "mobile/flutter.md" for r in recs)

    def test_deduplicates_recommendations_across_projects(self) -> None:
        data = _make_data(
            projects=[
                {
                    "encoded_path": "p1",
                    "decoded_path": "/p1",
                    "session_count": 5,
                    "prompt_count": 50,
                    "memory_file_count": 0,
                    "last_activity": "",
                    "tech_stack": ["python"],
                    "breakdown": {
                        "tool_usage": {},
                        "file_extensions": {".py": 20},
                        "agent_usage": {},
                        "model_usage": {},
                    },
                },
                {
                    "encoded_path": "p2",
                    "decoded_path": "/p2",
                    "session_count": 5,
                    "prompt_count": 50,
                    "memory_file_count": 0,
                    "last_activity": "",
                    "tech_stack": ["python"],
                    "breakdown": {
                        "tool_usage": {},
                        "file_extensions": {".py": 30},
                        "agent_usage": {},
                        "model_usage": {},
                    },
                },
            ]
        )

        recs = generate_recommendations(data)
        python_rules = [r for r in recs if r.name == "backend/python.md"]
        assert len(python_rules) == 1

    def test_skips_recommendations_when_project_claude_has_agent_locally(self) -> None:
        data = _make_data(
            projects=[
                {
                    "encoded_path": "test",
                    "decoded_path": "/projects/myapp",
                    "session_count": 5,
                    "prompt_count": 50,
                    "memory_file_count": 1,
                    "last_activity": "",
                    "tech_stack": ["python"],
                    "breakdown": {
                        "tool_usage": {},
                        "file_extensions": {".py": 40},
                        "agent_usage": {},
                        "model_usage": {},
                    },
                    "project_config": {
                        "has_claude_dir": True,
                        "has_claude_md": True,
                        "agents": ["python-pro"],
                        "rules": ["backend/python.md"],
                        "hook_count": 0,
                        "claude_md_keywords": [],
                    },
                }
            ]
        )

        recs = generate_recommendations(data)
        assert not any(r.name == "python-pro" for r in recs)
        assert not any(r.name == "backend/python.md" for r in recs)

    def test_lowers_confidence_when_claude_md_mentions_related_keywords(self) -> None:
        data = _make_data(
            projects=[
                {
                    "encoded_path": "test",
                    "decoded_path": "/projects/myapp",
                    "session_count": 5,
                    "prompt_count": 50,
                    "memory_file_count": 1,
                    "last_activity": "",
                    "tech_stack": ["python"],
                    "breakdown": {
                        "tool_usage": {},
                        "file_extensions": {".py": 80},
                        "agent_usage": {},
                        "model_usage": {},
                    },
                    "project_config": {
                        "has_claude_dir": False,
                        "has_claude_md": True,
                        "agents": [],
                        "rules": [],
                        "hook_count": 0,
                        "claude_md_keywords": ["python"],
                    },
                }
            ]
        )

        recs = generate_recommendations(data)
        py_rule = next((r for r in recs if r.name == "backend/python.md"), None)
        # Would be "high" (80 ops) but lowered because CLAUDE.md mentions python
        assert py_rule is not None
        assert py_rule.confidence == "medium"

    def test_limits_output_to_max_recommendations(self) -> None:
        data = _make_data(
            projects=[
                {
                    "encoded_path": "test",
                    "decoded_path": "/projects/polyglot",
                    "session_count": 10,
                    "prompt_count": 100,
                    "memory_file_count": 1,
                    "last_activity": "",
                    "tech_stack": ["python", "node", "go", "java", "dart"],
                    "breakdown": {
                        "tool_usage": {},
                        "file_extensions": {
                            ".py": 20,
                            ".ts": 20,
                            ".go": 20,
                            ".java": 20,
                            ".dart": 20,
                        },
                        "agent_usage": {},
                        "model_usage": {},
                    },
                }
            ]
        )

        recs = generate_recommendations(data)
        assert len(recs) <= 5
