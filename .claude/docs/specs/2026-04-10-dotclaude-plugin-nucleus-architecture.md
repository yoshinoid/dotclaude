---
title: dotclaude Plug-in Nucleus Architecture (Q3 수렴)
date: 2026-04-10
status: approved
version: 1
source: self-evolver-2026-04-10-q3 (25 loops, partial-max)
anchor_ref: user_dotclaude_q3_architecture_intent_anchor.md
---

# Spec: dotclaude Plug-in Nucleus Architecture (Q3 수렴)

## 1. 목표

**한 줄 요약:** dotclaude 를 thin Python core 위에 `EvolvePlugin` Protocol 을 구현한 plug-in 들이 얹히는 5-layer 아키텍처로 재편해, 사용자의 later 처리 파이프라인을 AI 가 오케스트레이션하는 플랫폼을 구축한다.

**동기:**

> "그러고보니 ai 오케스트레이션을 구성하면 내가 할일은 거의 later 처리겠네"
> — 사용자 발화 (2026-04-10, AI orchestration 렌즈 확정)

AI 오케스트레이션 성숙 후 사용자 역할은 later 큐 관리 + 방향 설정 + 승인으로 재편된다. dotclaude 는 그 파이프라인의 AI 오케스트레이터다. 현재 dotclaude 는 토큰 분석 도구에서 Claude Code 운영 플랫폼으로 전환 중이며, Q3 는 그 핵심 아키텍처인 Plug-in Nucleus 를 설계하는 단계다.

**가정:**
- Python 3.11+ 런타임 (project_python_migration.md: TS→Python 완료)
- Claude Code 가 주 실행 환경 (🧲 Claude-Code-Native)
- 주 25-40h 시간 예산 (본업 짬짬이), big-bang 전환 금지
- 현재 solo 개발 (🐝 Tribe 는 Phase 2)
- self-evolver 역할: spec-only (코드 구현 없음)

## 2. 범위 경계

### 포함
- 5-layer 아키텍처 모델 확정 및 계층 간 의존 규칙
- Layer 1 (dotclaude-core) 디렉토리 구조 및 모듈 역할
- Layer 2 (Plug-in Contract): `EvolvePlugin` Protocol + `Signal` / `WriteIntent` / `EvolvePlan` / `EvolveResult` 스키마
- `plugin.toml` manifest 포맷
- Trust Tier 시스템 (0/1/2/3): 경로 분류 → 자동/승인/차단 처리 + git rollback
- Later DB 스키마 (`later_items` 테이블, status 전환)
- Evolve Kernel 실행 흐름 (scan → propose → dry-merge → apply → gateway → flush)
- Thin Slice 샘플: 📊 Usage Plug-in 디렉토리·흐름 설계
- 15개 핵심 결정 (근거 포함)
- 14개 기각 대안 (기각 이유 포함)

### 미포함
- 실제 구현 코드 (이유: self-evolver Q3 결과물은 spec-only; 구현은 별도 `/plan` + executor 위임)
- 🐝 Tribe plug-in 구체 프로토콜 (이유: solo 상태, 지인 합류 후 검증 필요 — Phase 2)
- yoshinoid 다른 프로젝트 재사용 수준 확정 (이유: Q4 주제)
- Plug-in signing/allowlist 구체 메커니즘 (이유: 외부 plug-in 받을 시점에 재결정)
- Web UI 대시보드 구현 (이유: Phase 2 — later queue 관리 화면)
- `dry_merge` 충돌 해소 heuristic 구체화 (이유: 실 충돌 케이스 축적 후 진화)
- `kv_store` / `later_store` sqlite 파일 분리 여부 (이유: 구현 시 결정)
- 도메인·landing page (이유: yoshinoid 앵커 LATER)

> 범위 추가 시 이 섹션을 먼저 업데이트하고 변경 이력에 기록할 것.

## 3. 핵심 렌즈 — dotclaude = later 파이프라인 AI 오케스트레이터

dotclaude 7 키워드 전부를 later 파이프라인 구성요소로 재해석:

| 키워드 | later 파이프라인 역할 |
|---|---|
| 🧬 Self-Evolving Config | later 일부 자동 처리 (설정 진화 later 를 AI 가 직접) |
| 🛰️ Scout | 외부 신호 → 새 later 자동 생성 |
| 🐝 Tribe | 동료 later 패턴 학습 |
| 📊 Usage | 내 later 패턴 분석 |
| 🏰 Plug-in Nucleus | later 처리기들의 host |
| 🧲 Claude-Code-Native | later → Claude Code 실행 채널 |
| 🎯 Personalized by Design | 내 later 패턴에 맞춘 큐 관리 |
| 🧭 OSS Fatigue Killer | "도구 찾기" later 자체를 소멸시킴 |

**dotclaude UI 의 본질** = later 큐 관리 화면. 사용자가 하는 일 = 큐 우선순위 조정 + 승인/거부. 나머지는 AI.

## 4. 설계 상세

### 4.1 TL;DR

dotclaude 는 thin Python core (loader + event bus + evolve kernel + write gateway + later DB) 위에 `EvolvePlugin` Protocol (scan/propose/apply/explain) 을 구현한 plug-in 들이 얹히는 5-layer 아키텍처. 모든 파일 쓰기는 core 의 tiered write gateway 를 통해 git-commit 단위로 이뤄지고, later DB 가 single source of truth 가 되어 AI 가 생성한 PR draft 를 사용자가 아침에 리뷰하는 오케스트레이션 루프가 🧬 `evolve` 동사의 본체가 된다.

### 4.2 5-Layer 모델 (downward-only dependency)

```
Layer 5 — dotclaude-server (optional remote)
            Tribe sync · RAG pgvector · Web UI (later queue dashboard)
                          ▲ (HTTP, opt-in)
─────────────────────────── local-first boundary ────────────────────────
Layer 4 — Integration Surfaces (per-plugin, declarative)
            MCP servers · Hooks · Skills · Agents · Slash commands
                          ▲
Layer 3 — Built-in & Third-party Plug-ins
            usage · scout · tribe(Phase2) · recommendation · later-processor
            dotclaude.self (meta, dry-run only)
                          ▲
Layer 2 — Plug-in Contracts (pure Protocols + schemas)
            EvolvePlugin · Signal · EvolvePlan · WriteIntent · manifest
                          ▲
Layer 1 — dotclaude-core
            loader · event bus · config · classify_path · evolve kernel
            write gateway · later store (sqlite) · kv store
                          ▲
Layer 0 — Python 3.11+ runtime · Claude Code
```

**Dependency rule**: Layer 4/5 는 Layer 2 Protocol 만 import. Layer 3 plug-in 들 서로 직접 import 금지 — event bus 또는 core 경유. 이것이 hot-swap 의 전제 조건.

### 4.3 Layer 1 — dotclaude-core 디렉토리 구조

```
dotclaude-core/
├── dotclaude_core/
│   ├── __init__.py
│   ├── loader.py              # plug-in discovery, manifest parse, instantiate
│   ├── registry.py            # loaded plug-ins, lifecycle state
│   ├── event_bus.py           # asyncio-based pub/sub (adapter: local | redis)
│   ├── config.py              # dotclaude.toml schema (pydantic-settings)
│   ├── scheduler.py           # asyncio | thread | process dispatcher
│   ├── kv_store.py            # sqlite-backed plug-in state persistence
│   ├── later_store.py         # later DB (sqlite local, optional server sync)
│   ├── classify_path.py       # path → TrustTier (0/1/2/3) 단일 판정 함수
│   ├── write_gateway.py       # WriteIntent 인터셉트 → tier dispatch → git commit
│   ├── evolve_kernel.py       # scan → propose → dry-merge conflict → apply
│   ├── git_ops.py             # branch/commit/diff 래퍼 (dotclaude/evolve/*)
│   └── safety/
│       ├── sandbox.py         # timeout, memory limit, task isolation
│       ├── file_lock.py       # mtime + git-dirty 체크
│       └── permissions.py     # manifest write_paths vs 실제 intent 검증
└── pyproject.toml             # optional extras: [server], [redis], [mcp]
```

### 4.4 Layer 2 — Plug-in Contract (EvolvePlugin Protocol)

```python
# dotclaude_core/contracts.py  (Protocol — 타입 안전, in-process)

from typing import Protocol, Literal
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime

class Signal(BaseModel):
    source: str              # plug-in name
    kind: str                # "usage.hook_failure" | "scout.new_mcp" | ...
    payload: dict
    confidence: float        # 0..1
    collected_at: datetime

class WriteIntent(BaseModel):
    path: Path               # 대상 파일
    mode: Literal["create", "patch", "delete"]
    content: str | None      # patch 면 unified diff
    reason: str              # 왜 이걸 쓰려는지 (later explain 에 렌더링)

class EvolvePlan(BaseModel):
    plugin: str
    signals: list[Signal]
    intents: list[WriteIntent]
    tier_hint: Literal["auto", "review"] | None
    related_later_ids: list[str] = []

class EvolveResult(BaseModel):
    plan_id: str
    applied_intents: list[WriteIntent]
    skipped_intents: list[tuple[WriteIntent, str]]
    later_created: list[str]
    git_branch: str | None
    git_commits: list[str]

class EvolvePlugin(Protocol):
    name: str
    version: str

    async def scan(self, ctx: "PluginContext") -> list[Signal]: ...
    async def propose(self, signals: list[Signal], ctx: "PluginContext") -> EvolvePlan | None: ...
    async def apply(self, plan: EvolvePlan, ctx: "PluginContext") -> list[WriteIntent]: ...
    async def explain(self, plan: EvolvePlan) -> str: ...  # markdown
```

**핵심 불변식**: `apply()` 가 파일을 직접 쓰지 않는다. `WriteIntent` 리스트를 반환할 뿐. Core 의 `write_gateway` 가 수집 → `classify_path` → tier dispatch → atomic git commit.

### 4.5 Plugin Manifest (`plugin.toml`)

```toml
[plugin]
name = "dotclaude.usage"
version = "0.1.0"
scope = "personal"                  # personal | tribe
layer = "source"                    # source | processor | integration
execution_model = "asyncio"         # asyncio | thread | process
entry = "dotclaude_usage:UsagePlugin"

[plugin.channels]
hooks = ["post-session"]
skills = []
agents = []
commands = ["usage-report"]
mcp_servers = []

[plugin.permissions]
read_paths = ["~/.claude/logs/**", "~/.claude/memory/**"]
write_paths = ["~/.claude/memory/user_usage_*.md", "~/.claude/docs/reports/**"]
network = false

[plugin.dependencies]
core = ">=0.1.0"
plugins = []
```

Core 는 manifest 에 선언되지 않은 경로로의 write intent 를 `write_gateway` 에서 즉시 reject.

### 4.6 Trust Tier 시스템 (0/1/2/3)

| Tier | Paths | 처리 | Rollback |
|---|---|---|---|
| **0 auto** | `cache/**`, `reports/**`, `logs/derived/**` | 즉시 쓰기, git commit 없음 | 재실행 |
| **1 auto + git** | `memory/*.md`, `docs/later.md`, `docs/ideas.md` | `dotclaude/evolve/YYYY-MM-DD` 브랜치 auto commit | `git revert` |
| **2 review** | `rules/**`, `agents/**`, `skills/**`, `CLAUDE.md`, `hooks/**` | `dotclaude/later/{slug}` 브랜치 + PR draft + later row (`pending_approval`) | PR close |
| **3 blocked** | `.env*`, `*.pem`, `*_secret*`, `*_key*`, `.git/config` | **Reject at gateway** | N/A |

Tier 시스템이 `feedback_no_approval` (자율 선호) 과 `feedback_always_review` (리뷰 필수) 의 구조적 충돌을 해소.

### 4.7 Later DB 스키마 (later_store)

```sql
CREATE TABLE later_items (
    id TEXT PRIMARY KEY,                    -- slug
    title TEXT NOT NULL,
    body TEXT,                              -- markdown
    source_plugin TEXT NOT NULL,
    signal_refs TEXT,                       -- JSON array
    tier INTEGER NOT NULL,                  -- 0|1|2
    status TEXT NOT NULL,                   -- proposed|pending_approval|applied|rejected|stashed
    branch TEXT,                            -- dotclaude/later/{slug}
    pr_url TEXT,
    explain_md TEXT,                        -- EvolvePlugin.explain() 결과
    ai_priority REAL,                       -- 0..1 AI 제안
    user_priority REAL,                     -- 사용자 덮어씀 (NULL = AI 값 사용)
    tags TEXT,                              -- JSON
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX idx_later_status ON later_items(status);
CREATE INDEX idx_later_tier ON later_items(tier);
```

status 전환 시 event bus 에 publish → 다른 plug-in 이 subscribe 가능 (feedback loop).

### 4.8 Evolve Kernel 실행 흐름

```
1. scheduler.tick()
   └─ for each loaded plug-in: await plugin.scan() → Signals
2. event_bus.publish("signal.new", signals)
3. for each plug-in subscribing to these signals:
     plan = await plugin.propose(signals)
4. evolve_kernel.collect_plans() → [EvolvePlan, ...]
5. dry_merge(plans) → conflict detection
      ├─ no conflict: proceed
      └─ conflict: 충돌 모두 Tier 2 로 escalate (both to later.pending_approval)
6. for each plan:
     intents = await plugin.apply(plan)
     for intent in intents:
         tier = classify_path(intent.path)
         if tier == 3: reject + log
         elif tier == 0: write_gateway.write_raw(intent)
         elif tier == 1: write_gateway.stage(intent, branch="evolve/YYYY-MM-DD")
         elif tier == 2:
             later_store.create(intent, status="pending_approval",
                                branch="later/{slug}",
                                explain_md=await plugin.explain(plan))
             git_ops.create_branch_with_commit(intent)
7. write_gateway.flush() → single git transaction per tier bucket
8. event_bus.publish("evolve.completed", EvolveResult)
```

### 4.9 Thin Slice 샘플 — 📊 Usage Plug-in

```
dotclaude-usage/
├── pyproject.toml
├── plugin.toml
└── dotclaude_usage/
    ├── __init__.py
    ├── plugin.py                         # UsagePlugin(EvolvePlugin)
    ├── scanners/
    │   ├── hook_failure_scanner.py       # ~/.claude/logs 파싱
    │   └── command_frequency_scanner.py
    ├── proposers/
    │   └── memory_update_proposer.py     # Signal → EvolvePlan
    └── templates/
        └── usage_report.md.j2
```

**End-to-end 시나리오**:
1. `scan()`: `~/.claude/logs/` 에서 어제자 hook 실패 3건 감지 → `Signal(kind="usage.hook_failure", ...)`
2. `propose()`: `memory/user_usage_patterns.md` 에 추가할 패치 + `docs/reports/2026-04-11.md` 신규 생성 → `EvolvePlan` with 2 `WriteIntent`
3. core: `classify_path("memory/user_usage_patterns.md")` → Tier 1, `classify_path("docs/reports/...")` → Tier 0
4. `apply()`: WriteIntent 리스트 반환 (파일 안 씀)
5. gateway: Tier 0 은 즉시 쓰기, Tier 1 은 `dotclaude/evolve/2026-04-11` 브랜치 commit
6. `explain()`: "지난 24시간 post-commit hook 3건 실패. 원인 패턴 ... 메모리에 기록했습니다."
7. 사용자는 아침에 `dotclaude morning` 실행 → Tier 1 auto-commit 요약 + Tier 2 pending PR draft 표시

## 5. 결정 사항

### 5.1 Key Decisions (15)

| # | 항목 | 결정 | 대안 (기각 이유) |
|---|---|---|---|
| Q1 | Core/Plug-in 경계 | Thin core + 🧬 evolve kernel | (a) minimal kernel: 🧬 도 plug-in → Core 정체성 희석, evolve 동사 격하. (c) feature-rich core: Idea Sandbox + Plug-in Nucleus 키워드와 충돌 |
| Q2 | Plug-in 계약 방식 | Hybrid: Python Protocol (in-process) + MCP (외부/타언어) | 순수 Protocol: 외부 언어 plug-in 불가 → 🧲 약화. 순수 MCP: in-process 오버헤드, 타입 안전 상실 |
| Q3 | Write-back 신뢰 경계 | Tiered (0/1/2/3) + git auto-commit + sandbox branch | Full-auto: Tier 2 파일 무승인 = always_review 위반. 항상 diff+approve: no_approval 위반, 승인 피로 누적 |
| Q4 | Scout 실행 모델 | Server 주 (scraping·임베딩·pgvector) + 로컬 보조 (개인 맥락) | 로컬 cron only: 머신-off gap, tribe 공유 불가. server-only: 오프라인 개인 맥락 접근 불가 |
| Q5 | Claude Code 통합 채널 | All-of-the-above, plug-in manifest 에서 채널 선언 | MCP only: hook·skill 의 Claude Code native 장점 포기 |
| Q6 | State/Storage 경계 | Split by type (개인→local, tribe·RAG→server, 명시 공유→bidirectional) | local-first all: tribe 불가. server-authoritative: 오프라인 개발 불가. bidirectional all: 충돌 해소 복잡도 폭증 |
| Q7 | later 파이프라인 위치 | 별도 later DB (single source of truth) + later.md markdown view + PR/branch 자동 생성 | later.md 가 queue: 멀티 머신 sync 불가, 구조화 쿼리 불가. AI 자동 커밋: Tier 2 always_review 위반 |
| Q8 | MVP 범위 | Architecture spec only + thin slice 샘플 1개 (Usage) | 전체 thin slice 구현: self-evolver 역할 범위 밖 (spec only). abstract spec 만: "정말 되나" 검증 불가 |
| D9 | Layer 의존 방향 | 5-layer + downward-only dependency | 양방향 import: hot-swap 불가, 테스트 격리 붕괴 |
| D10 | EvolvePlugin 메서드 구성 | 4-method Protocol: scan/propose/apply/explain | 2-method (scan+apply): evolve 동사 구체화 불충분, 설명 가능성(explain) 없음 |
| D11 | 파일 쓰기 주체 | plug-in 은 WriteIntent 반환, gateway 가 실제 write | plug-in 이 직접 파일 쓰기: tier 일관성·감사 추적·permission 검증 불가 |
| D12 | dotclaude.self meta plug-in | dry-run only 모드 포함 | self-hosting 완전 허용: 부트스트랩 루프 (자기가 자신의 아키텍처를 무한 수정) |
| D13 | Later status → event bus | status 전환 시 event bus publish | 폴링 방식: feedback loop 지연, plug-in 연동 부재 |
| D14 | max_pending_approvals 소프트 캡 | AI clustering + 소프트 캡으로 승인 피로 방지 | 무제한 쌓기: 사용자 인지 부하 → later 큐 폐기 |
| D15 | 이관 전략 | Legacy monolith plug-in wrapping (점진 이관) | Big-bang 전환: 시간 예산 초과, 포트폴리오 회귀 위험 |

### 5.2 Rejected Alternatives (14)

| 대안 | 기각 이유 |
|---|---|
| Minimal kernel (🧬도 plug-in) | 🧬 의 Core 정체성 훼손 — evolve 는 dotclaude 의 유일 동사 |
| Feature-rich core (VSCode 스타일) | Idea Sandbox + Plug-in Nucleus 키워드와 직접 충돌 |
| 순수 Python Protocol only | 외부 언어 plug-in 불가 → 🧲 약화 |
| 순수 MCP server only | in-process 간단 plug-in 오버헤드, 타입 안전 상실 |
| Full-auto write-back (야간 배치) | Tier 2 파일 무승인 = always_review 위반 |
| 항상 diff + approve | no_approval 위반, 승인 피로 누적 |
| 로컬 cron only scout | 머신-off gap, tribe 공유 불가 |
| Server-only state | 오프라인 개발 불가, local 편집 UX 파괴 |
| later.md 가 queue (DB 없음) | 멀티 머신 sync 불가, 구조화 쿼리 불가 |
| AI 처리 = 제안만 | orchestration 렌즈 "실행 위임" 목적 불일치 |
| AI 처리 = 무승인 자동 커밋 | Tier 2 always_review 위반 |
| Plug-in 이 직접 파일 쓰기 | tier 일관성·감사 추적·permission 검증 불가 |
| Big-bang 아키텍처 전환 | 시간 예산 초과, 포트폴리오 회귀 위험 |
| Full-thin slice 구현 (코드 작성) | self-evolver 역할 범위 밖 (spec only) |

## 6. 태스크

| # | 태스크 | 레포/파일 | 의존 | 상태 |
|---|---|---|---|---|
| T1 | dotclaude-core 레포 초기화 (pyproject.toml, 패키지 구조) | dotclaude-core/ | — | ⬜ |
| T2 | contracts.py 구현 (Signal, WriteIntent, EvolvePlan, EvolveResult, EvolvePlugin Protocol) | dotclaude-core/dotclaude_core/contracts.py | T1 | ⬜ |
| T3 | classify_path.py 구현 (Tier 0/1/2/3 판정 로직) | dotclaude-core/dotclaude_core/classify_path.py | T1 | ⬜ |
| T4 | write_gateway.py 구현 (WriteIntent 인터셉트 → tier dispatch) | dotclaude-core/dotclaude_core/write_gateway.py | T2, T3 | ⬜ |
| T5 | git_ops.py 구현 (branch/commit/diff 래퍼) | dotclaude-core/dotclaude_core/git_ops.py | T1 | ⬜ |
| T6 | later_store.py 구현 (sqlite 스키마, CRUD, status 전환 + event bus publish) | dotclaude-core/dotclaude_core/later_store.py | T1 | ⬜ |
| T7 | event_bus.py 구현 (asyncio.Queue 기반, redis adapter 인터페이스) | dotclaude-core/dotclaude_core/event_bus.py | T1 | ⬜ |
| T8 | loader.py + registry.py 구현 (plugin.toml 파싱, EvolvePlugin 인스턴스화) | dotclaude-core/dotclaude_core/loader.py | T2 | ⬜ |
| T9 | evolve_kernel.py 구현 (scan → propose → dry-merge → apply 흐름) | dotclaude-core/dotclaude_core/evolve_kernel.py | T4, T6, T7, T8 | ⬜ |
| T10 | safety/ 모듈 구현 (sandbox, file_lock, permissions) | dotclaude-core/dotclaude_core/safety/ | T3, T4 | ⬜ |
| T11 | dotclaude-usage thin slice 구현 (UsagePlugin, scanners, proposers) | dotclaude-usage/ | T2, T8, T9 | ⬜ |
| T12 | 단위 테스트 (contracts, classify_path, write_gateway, later_store) | dotclaude-core/tests/ | T2~T6 | ⬜ |
| T13 | end-to-end 시나리오 검증 (Usage plug-in 아침 루프 시뮬레이션) | dotclaude-core/tests/e2e/ | T11, T12 | ⬜ |
| T14 | dotclaude-core 를 기존 dotclaude CLI 에 plug-in wrapping 연결 (점진 이관) | dotclaude/src/dotclaude/ | T9 | ⬜ |

상태 기호: ⬜ 대기 / 🔄 진행 / ✅ 완료 / ❌ 차단

## 7. 의존성 (멀티 레포)

| 순서 | 레포 | 작업 | 배포 순서 |
|---|---|---|---|
| 1 | dotclaude-core (신규) | 5-layer core + contracts + kernel | 로컬 설치 우선 |
| 2 | dotclaude-usage (신규) | Usage thin slice plug-in | dotclaude-core 설치 후 |
| 3 | dotclaude (기존 CLI) | plug-in wrapping + 점진 이관 | dotclaude-core 설치 후 |
| 4 | dotclaude-server (기존) | later DB sync API + Scout 주 실행 | T6 later_store 완료 후 |

## 8. 검증 기준

`/verify` 에서 확인할 항목:

- [ ] `classify_path("~/.claude/memory/foo.md")` → Tier 1 반환
- [ ] `classify_path("~/.claude/.env")` → Tier 3 반환 (reject)
- [ ] `write_gateway` 가 Tier 3 WriteIntent 를 reject + 로그 기록
- [ ] Tier 1 WriteIntent 실행 시 `dotclaude/evolve/YYYY-MM-DD` 브랜치 존재 확인 (`git branch --list`)
- [ ] Tier 2 WriteIntent 실행 시 `later_items` 에 `status=pending_approval` 행 생성 확인
- [ ] UsagePlugin.scan() 이 `~/.claude/logs/` 에서 Signal 리스트 반환 (mock log 기준)
- [ ] UsagePlugin.apply() 가 파일을 직접 쓰지 않고 WriteIntent 리스트만 반환
- [ ] `evolve_kernel` dry_merge 충돌 시 두 plan 모두 Tier 2 escalate 확인
- [ ] plug-in manifest 에 없는 경로 write 시 permissions.py 가 거부
- [ ] `later_store` status 전환 시 event_bus 에 이벤트 publish 확인

## 9. 리스크 & 완화

| 리스크 | 영향 | 완화 방안 |
|---|---|---|
| git_ops 실패 시 Tier 1 데이터 유실 | 높음 | atomic flush + rollback 로직. 실패 시 Tier 2 degradation |
| sqlite later_store 멀티 프로세스 경합 | 중간 | WAL mode + file_lock.py 로 직렬화 |
| plug-in 무한 루프 (dotclaude.self 가 자신을 수정) | 높음 | dotclaude.self 는 dry-run only. evolve_kernel 에 depth limit |
| 승인 피로 (Tier 2 항목 과다 누적) | 중간 | max_pending_approvals 소프트 캡 + AI clustering |
| 레거시 CLI 코드와 신규 core 충돌 | 중간 | plug-in wrapping 레이어 격리, big-bang 전환 금지 |
| time budget 초과 (주 25-40h) | 높음 | T1-T3 먼저 (contracts 우선), thin slice 완성 후 점진 |

## 10. 미결 질문

| # | 질문 | 담당 | 기한 |
|---|---|---|---|
| Q1 | Plug-in 배포 채널 (git+ssh vs PyPI vs Claude Code plugin marketplace) | 사용자 | Phase 2 시작 전 |
| Q2 | later.md 파일 경로 고정 vs dotclaude.toml config override 허용 | 사용자 | T6 구현 전 |
| Q3 | event bus 구현체 선택 (asyncio.Queue 내장 vs pyee vs redis) | 사용자 | T7 구현 전 |
| Q4 | Plug-in signing/allowlist 구체 메커니즘 | 사용자 | 외부 plug-in 수용 시점 |
| Q5 | `dry_merge` 충돌 해소 heuristic 구체화 | 사용자 | 실 충돌 케이스 5건 이상 축적 후 |
| Q6 | kv_store 와 later_store sqlite 파일 분리 여부 | 사용자 | T1 구현 시 |

> Q1–Q3 는 `~/.claude/docs/later.md` Deferred (self-evolver) 섹션과 연결됨.

## 11. 수렴 근거 (Convergence Evidence)

- **Total loops**: 25 / 25 (partial-max, 3-연속 empty 직전 종료, 실질 포화)
- **Empty loops**: 14, 18, 23, 24, 25
- **Novel insights accumulated**: 20
- **Angles covered**: competitive, MVP, verb-centric, hierarchy, user-scenario, risk, constraint, plug-in-lifecycle, write-back-safety, later-pipeline-ux, meta-recursive, migration-cost, explainability (base 7 + 특화 5 + 재방문 6)
- **Session ID**: `self-evolver-2026-04-10-q3`
- **결정 방식**: 사용자가 판단을 SEB agent 에 위임 ("모두 seb진행해서 가장최적으로 진행해줘"). 각 답은 memory anchors + 7 keywords + AI orchestration 렌즈 + 목표함수로부터 도출.

## 12. 연기된 항목 (Deferred)

`~/.claude/docs/later.md` — `## Deferred (self-evolver)` 섹션에 저장된 3개 항목:

1. **Plug-in 배포 채널** (git+ssh vs PyPI vs Claude Code plugin marketplace) — default: git + marketplace 병행, PyPI 보류 (이름 충돌 이슈). `plugin.toml` `source` 필드 값 범위에 minor impact.
2. **later.md 파일 경로** 고정 vs config override — default: 기본값 `~/.claude/docs/later.md`, `dotclaude.toml` 의 `later.view_path` 오버라이드 허용. config schema 1-2 필드에 minor impact.
3. **Event bus 구현체** (asyncio.Queue vs pyee vs redis) — default: asyncio.Queue 내장 + redis adapter optional. 의존성 1개 (redis-py) 를 optional extra 로.

## 13. 잔존 불확실성 (Remaining Structural Uncertainty)

- **Plug-in signing/allowlist**: 외부 plug-in 수용 시점에 재결정. 현재 local/git plug-in 만이므로 blocking 아님.
- **dry_merge heuristic**: 현재 "충돌 시 both escalate to Tier 2". 실 충돌 케이스 5건+ 축적 후 진화.
- **kv_store / later_store sqlite 파일 분리**: 구현 시 결정. 성능 이슈 없으면 단일 파일 유지.

## 14. 의도적으로 열어둔 항목 (Intentionally Open)

- 🐝 Tribe plug-in 구체 프로토콜 — Phase 2 (solo 상태, 지인 합류 후 검증)
- yoshinoid 다른 프로젝트 재사용 수준 — Q4 주제
- 도메인·landing page — yoshinoid 앵커 LATER
- `dotclaude morning` CLI 명령 UX 상세 — T9 이후 설계

## 15. 다음 단계

1. `/plan dotclaude-core 레포 초기화 + contracts.py 구현` — planner + critic 으로 T1-T2 계획 수립
2. T1-T3 (core init + contracts + classify_path) 선행 구현 → verifier 검증
3. T4-T6 (write_gateway + git_ops + later_store) 구현
4. T11 (Usage thin slice) 구현 → end-to-end 시나리오 검증 (T13)
5. T14 (기존 dotclaude CLI 점진 이관)

> 구현 시작 전 미결 Q2(later.md 경로), Q3(event bus 구현체) 사용자 확인 권장.

## 16. 변경 이력

| 날짜 | 버전 | 변경 | 이유 |
|---|---|---|---|
| 2026-04-10 | 1 | 초안 생성 (self-evolver Q3 25-loop 수렴 결과 spec 화) | 사용자 승인 ("가자!") |
| 2026-04-11 | 1.1 | dotclaude-core Phase 0 구현 범위 한정으로 **Plugin → Extension naming rename note** | Phase 0 implementation plan v2 (planner Round 2 + critic Round 2 CONDITIONAL APPROVAL) 에서 기존 `dotclaude/src/dotclaude/parser/parsers/plugins.py:PluginsStatus` (Claude Code marketplace plug-in 파싱) 와 어휘 격리 필요. dotclaude-core 구현에서: `EvolvePlugin` Protocol → `EvolveExtension`, `plugin.toml` → `extension.toml`, `loader.py` → `extension_loader.py`, `registry.py` → `extension_registry.py`. **본 spec 본문 (T1-T14, §4 등) 의 "Plugin / plug-in" 단어는 미변경** — Q3 spec 의 전면 rename 은 별도 patch 로 다룸. 이 행은 dotclaude-core Phase 0 구현 범위에 한정된 alias note. |

---

## References

### 메모리 파일
- `~/.claude/projects/C--Users-jeong-projects-yoshinoid/memory/user_dotclaude_q3_architecture_intent_anchor.md` — **Phase 1 앵커 8개 + 근거** (이 spec 의 결정 근거)
- `~/.claude/projects/C--Users-jeong-projects-yoshinoid/memory/user_dotclaude_keywords.md` — 7 키워드 4 계층 (🧬🛰️🐝📊🏰🧲🎯🧭)
- `~/.claude/projects/C--Users-jeong-projects-yoshinoid/memory/user_ai_orchestration_role.md` — AI 오케스트레이션 렌즈 (★ 중요도 최상)
- `~/.claude/projects/C--Users-jeong-projects-yoshinoid/memory/user_identity_vision.md` — 개발자 아이덴티티 7축 + 목표함수
- `~/.claude/projects/C--Users-jeong-projects-yoshinoid/memory/project_dotclaude_state.md` — dotclaude 5 레포 현황 + Q3 Architecture 대기 맥락

### 연결 문서
- `~/.claude/docs/later.md` — Deferred (self-evolver) 섹션: Q1-Q3 미결 항목
- `C:\Users\jeong\projects\yoshinoid\dotclaude-rag\.claude\docs\specs\2026-04-09-phase1-knowledge-pipeline.md` — RAG phase1 spec (형식 참조)

### 브레인스토밍 세션 메타
- **세션 날짜**: 2026-04-10
- **에이전트**: self-evolver (SEB — self-evolving-brainstorm)
- **세션 ID**: `self-evolver-2026-04-10-q3`
- **루프 수**: 25 (partial-max, 실질 포화)
- **수렴 트리거**: 3-연속 empty loop (14, 18, 23, 24, 25 에서 empty 시작)
- **사용자 승인**: "가자!" (2026-04-10)
