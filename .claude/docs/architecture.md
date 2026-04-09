# dotclaude CLI — Architecture
> Updated: 2026-04-09 | Stack: Python 3.11+, Typer, Rich, Pydantic v2, httpx

## System Overview
```
~/.claude/ (local data)
    │
    ├── projects/         conversations.jsonl per project
    ├── sessions/         session metadata
    ├── history.jsonl     prompt history
    ├── agents/           custom agent definitions
    ├── rules/            coding rules
    ├── commands/         slash commands
    ├── skills/           reusable prompt templates
    └── settings.json     hooks, MCP servers

    ↓ parse & analyze

dotclaude CLI
    ├── parser/           stream JSONL → aggregate stats
    ├── insights/         signal detection + Gemini AI analysis
    ├── display/          Rich dashboard + HTML report
    └── commands/         analyze, insights, sync, config, login, register, serve

    ↓ sync (optional)

dotclaude-server /api/sync  (JWT auth)
```

## Directory Structure
```
src/dotclaude/
├── cli.py                  Typer app entry point
├── models.py               Re-export shim → dotclaude_types.models
├── commands/
│   ├── analyze.py          Main analysis command (--json, --html, --serve)
│   ├── insights.py         AI insights (local signals + Gemini)
│   ├── config.py           API key management
│   ├── login.py            Server auth (JWT)
│   ├── register.py         Server account creation
│   ├── sync.py             Upload snapshot to server
│   └── serve.py            Local HTTP dashboard server
├── parser/
│   ├── __init__.py         analyze() → DotClaudeData (public API)
│   ├── scanner.py          Walk ~/.claude directory tree
│   ├── pricing.py          Token cost calculations per model
│   ├── utils.py            JSONL streaming, path normalization
│   └── parsers/            Domain parsers:
│       ├── conversations.py  JSONL → prompts, tokens, tools, costs
│       ├── configs.py        agents, commands, rules, skills, MCP
│       ├── projects.py       per-project stats + tech stack detection
│       ├── settings.py       hooks from settings.json
│       ├── plugins.py        blocklist, marketplaces
│       ├── subagents.py      subagent .meta.json
│       └── process_sessions.py  session PIDs, durations
├── insights/
│   ├── signals.py          Rule-based signal detection (thresholds)
│   ├── recommendations.py  Catalog-based config suggestions
│   ├── gemini.py           Gemini API client for AI insights
│   ├── anonymize.py        Strip PII before sending to Gemini
│   └── config_store.py     Gemini API key persistence
└── display/
    ├── dashboard.py        Rich terminal dashboard
    ├── html_report.py      Self-contained HTML report
    └── formatters.py       Numbers, tokens, costs, sparklines
```

## Data Flow
```
1. scanner.py     → walk dirs, collect file paths
2. parsers/*      → stream JSONL files, aggregate into typed dicts
3. __init__.py    → assemble DotClaudeData from all parser outputs
4. dashboard.py   → render Rich panels to terminal
   html_report.py → generate standalone HTML file
   insights/      → detect signals + optional Gemini analysis
```

## Type Sharing
- All models live in `dotclaude-types` package (import: `dotclaude_types.models`)
- `src/dotclaude/models.py` is a backward-compat re-export shim
- Server imports same types — single source of truth

## External Connections
| Service | When | Auth |
|---------|------|------|
| dotclaude-server | `sync`, `login`, `register` | JWT (access + refresh) |
| Gemini API | `insights --ai` | API key in ~/.config/dotclaude/ |

## Gotchas
- JSONL files can be very large (100MB+) — streaming parser, never load full file
- Windows paths use backslashes — `normalize_cwd()` handles this
- `orjson` used for JSONL parsing performance (cross-platform wheel available)
- camelCase alias on all models for JSON compat with TS-era API
