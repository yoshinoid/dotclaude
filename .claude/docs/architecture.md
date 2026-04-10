# dotclaude CLI — Architecture
> Updated: 2026-04-11 | Phase 1-3 완료 · yoshinoid Phase 0 T1-T3 구현 중 | Stack: Python 3.11+, Typer, Rich, Pydantic v2, httpx

## Workspace 구조 (2026-04-11 기준 5 sub-repos)

```
yoshinoid/  (workspace root, multi-repo)
│
├── dotclaude/          ← 이 레포 — end-user CLI + Phase 0 spec 허브
├── dotclaude-types/    ← Shared Pydantic v2 models (CLI + server 공용)
├── dotclaude-rag/      ← RAG 엔진: chunker, embedding, frontmatter, vector search
├── dotclaude-server/   ← FastAPI backend + React web dashboard
└── dotclaude-core/     ← 2026-04-11 신규 — yoshinoid meta-agent "evolve kernel"
                           (Phase 0 Track 1 구현 중, T1-T3 landed)
```

**레포 분화 이유**: `dotclaude` 는 사용자가 직접 호출하는 CLI 본체, `dotclaude-core` 는
확장(Extension)들이 얹히는 런타임 커널. 두 레포는 의존성 방향이 반대 — core 는
dotclaude 의 내부를 모르고, dotclaude 는 core 의 API 를 사용만 함. 상세는
`specs/2026-04-10-dotclaude-plugin-nucleus-architecture.md` (Q3 v1.1) 와
`specs/2026-04-11-yoshinoid-phase-0-implementation-plan.md` (v1.2) 참조.

## System Overview
```
~/.claude/ (local data)
    │
    ├── projects/         conversations.jsonl per project
    ├── sessions/         session metadata
    ├── history.jsonl     prompt history
    ├── agents/           custom agent definitions (+ yoshinoid.md 예정, Track 2)
    ├── memory/           (예정) yoshinoid_{state,patterns,corrections}.md
    ├── hooks/            (+ yoshinoid-writer.sh 예정, Track 2 TT2-1)
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

    ↓ sync (optional)           ↓ (future, Phase 0.5+) extension load

dotclaude-server /api/sync       dotclaude-core evolve kernel
(JWT auth)                        └── EvolveExtension Protocol
                                      └── dotclaude-usage (thin slice)
```

## Directory Structure
```
src/dotclaude/
├── cli.py                  Typer app entry point
├── models.py               Re-export shim → dotclaude_types.models
├── commands/
│   ├── analyze.py          Main analysis command (--json, --html, --serve)
│   ├── insights.py         AI insights + --evolve (서버+로컬 추천 병합)
│   ├── config.py           API key management
│   ├── login.py            Server auth (JWT)
│   ├── register.py         Server account creation
│   ├── sync.py             Upload snapshot + knowledge (Phase 1 확장)
│   ├── format.py           Phase 1: dc_ frontmatter 자동 적용
│   ├── team.py             Phase 3a: create/join/leave/list
│   ├── pull.py             Phase 3b: pull + workflow (approve/reject/status)
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
│   ├── signals.py          Rule-based signal detection (레거시 — rag로 이전 예정)
│   ├── recommendations.py  Catalog-based config suggestions (로컬 폴백)
│   ├── server_recommendations.py  서버 추천 API fetch (Phase 2)
│   ├── merge.py            서버 + 로컬 추천 병합 (title+type dedup, max 7)
│   ├── gemini.py           Gemini API client for AI insights
│   ├── anonymize.py        Strip PII before sending to Gemini
│   └── config_store.py     Gemini API key persistence
├── utils/
│   └── file_writer.py      Phase 3b: safe_write (path traversal 방지 + .bak)
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
| dotclaude-server | `sync`, `login`, `register`, `team`, `pull`, `--evolve` | JWT (access + refresh) |
| Gemini API | `insights --ai` | API key in ~/.config/dotclaude/ |
| dotclaude-rag | `format`, `sync` (frontmatter 처리) | 패키지 의존성 |
| dotclaude-core | (future) evolve kernel runtime — 확장 로드 / 시그널 수집 / write gateway | 패키지 의존성 (Phase 0.5+) |

## yoshinoid Meta-Agent Family (Phase 0, 2026-04-11)

yoshinoid 는 단일 서브 에이전트가 아니라 **meta-agent family 의 kernel** 로 설계됨.
Family SEB Round 1 (2026-04-11) 수렴 결과:

```
                 yoshinoid kernel
                      │
     ┌────────────────┼────────────────┐
     │                │                │
  present           past            future-seeds
 (lens: secretary) (lens: career)  (lens: idea-manager)
                                   ← 가장 먼저 배포 (Phase 0.5)
```

- **Kernel** (dotclaude-core) — 공통 인프라: `Signal` 수집, `WriteIntent` 발행,
  `classify_path` tier 0/1/2/3, `write_gateway` dispatch, `later_store` sqlite,
  `event_bus` asyncio.Queue, `extension_loader` (`extension.toml` 스캔),
  `evolve_kernel` (scan → propose → dry_merge → apply)
- **Lens** = specialization: 각 에이전트가 특정 도메인 · 데이터소스 · 출력 형식을
  담당. Lens 간 직접 호출 금지 — kernel-mediated communication only.

**네이밍 HARD** (plan §1): `EvolveExtension` Protocol, `extension.toml` manifest,
`extension_loader/registry`. 기존 `parser/parsers/plugins.py:PluginsStatus`
(Claude Code marketplace 파서) 와 어휘 격리.

**진행 현황** (2026-04-11):
- Track 1 (dotclaude-core): T1-T3 landed (`502c333`), T10a → T4 → T9 → T13 → V
  남음
- Track 2 (yoshinoid kernel `~/.claude/` 배포): TT2-1 ~ TT2-5 전부 대기 중
  (글로벌 수정이라 명시 승인 필요)
- Phase 0.5 (idea-manager lens): Phase 0 완료 후 진입
- Phase 1 (career lens, 공유/제품화 가능성 ★): Phase 0.5 이후
- Phase 2+ (secretary lens): 가장 무거움, 나중

상세: `.claude/docs/specs/2026-04-11-yoshinoid-phase-0-implementation-plan.md`

## Gotchas
- JSONL files can be very large (100MB+) — streaming parser, never load full file
- Windows paths use backslashes — `normalize_cwd()` handles this
- `orjson` used for JSONL parsing performance (cross-platform wheel available)
- camelCase alias on all models for JSON compat with TS-era API
- **dotclaude-core 는 별도 레포** — 이 `dotclaude/` 레포의 `src/dotclaude/` 와
  namespace 가 다름. core 는 `dotclaude_core` 패키지로 import
