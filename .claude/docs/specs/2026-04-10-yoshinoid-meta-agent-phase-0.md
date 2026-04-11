---
title: yoshinoid Meta-Agent Phase 0 Thin Slice
date: 2026-04-10
status: approved (v2.2 — 2026-04-11 late rename cascade terminology note 추가. content 는 historical preserve)
version: 2.2
id: 2026-04-10-yoshinoid-meta-agent-phase-0
owner: jeonghwan-hwang (yoshinoid)
source: self-evolver-brainstorm (v1: 25 loops; v2: 14 loops family reframe) + critic (CONDITIONAL APPROVAL) + internet-research (5 sources) + 2026-04-11 knowledge rename cascade terminology integration (v2.2)
related_specs:
  - 2026-04-10-dotclaude-plugin-nucleus-architecture.md (v1.2 — terminology note 추가됨)
  - 2026-04-10-dotclaude-yoshinoid-flagship-alignment.md
  - 2026-04-11-yoshinoid-phase-0-implementation-plan.md (v1.3 — T6 knowledge_store 통합)
  - 2026-04-11-knowledge-store-separation-and-rename-cascade.md (v1 — rename cascade canonical spec)
related_rules:
  - ~/.claude/rules/agent-skill-creation.md
  - ~/.claude/rules/knowledge.md (구 logbook.md, v3 rewrite)
related_docs:
  - ~/.claude/knowledge/working/later.md (★★ yoshinoid 섹션, 2026-04-11 rename 이후 경로)
  - ~/.claude/projects/c--Users-jeong-projects-yoshinoid/memory/project_meta_agent_family.md
  - ~/.claude/projects/c--Users-jeong-projects-yoshinoid/memory/user_knowledge_store_separation_intent_anchor.md (★ intent lock)
---

# Spec: yoshinoid Meta-Agent Phase 0 Thin Slice

---

## 0. Terminology note (v2.2, 2026-04-11 rename cascade)

2026-04-11 late 에 **logbook → knowledge** 원자적 rename cascade 가 실행됨 (spec `2026-04-11-knowledge-store-separation-and-rename-cascade.md`). 본 spec 의 기존 "logbook" / "`~/.claude/docs/`" 참조는 다음과 같이 읽어야 함:

- `yoshinoid/logbook` repo → `yoshinoid/knowledge` repo
- `~/.claude/rules/logbook.md` → `~/.claude/rules/knowledge.md`
- `~/.claude/docs/later.md` → `~/.claude/knowledge/working/later.md`
- `~/.claude/docs/ideas.md` → `~/.claude/knowledge/working/ideas.md`
- `~/.claude/docs/research.md` → `~/.claude/knowledge/working/research.md`
- `~/.claude/docs/` (전역 working set) → `~/.claude/knowledge/working/` (local) + `yoshinoid/knowledge` (remote)
- §7.2 C7b 의 "logbook repo" 언급 → "**knowledge repo** (`~/.claude/knowledge/` local + `yoshinoid/knowledge` remote)"
- §5 "brand 파일" 의 `~/.claude/docs/` → `~/.claude/knowledge/` 내부 (manifesto.md 등)
- §17 lens primary owner 경로의 `~/.claude/docs/ideas.md` → `~/.claude/knowledge/working/ideas.md`

본문은 **content 보존 원칙**에 따라 수정하지 않음. 독자는 이 terminology note 와 함께 읽을 것. 현재 canonical 은 `2026-04-11-knowledge-store-separation-and-rename-cascade.md`.

---

## 1. 목표

**한 줄 요약:** yoshinoid 라는 이름의 meta-agent 를 `~/.claude/agents/yoshinoid.md` 에 구현하고, 사용 패턴 관찰 + 사전 제안 + 인지 부하 절감을 검증하는 Phase 0 최소 구조를 완성한다.

**동기:**

사용자의 AI 오케스트레이션 성숙 단계에서 인지 부하의 마지막 층은 "어떤 에이전트를 다음에 호출해야 하는가"이다. yoshinoid 는 이 층을 자율적으로 흡수하는 meta-orchestrator 다.

Q3 Plug-in Nucleus 와 Q4 Flagship Alignment 로 dotclaude 아키텍처와 yoshinoid 랩 포지셔닝이 확정된 상태에서, yoshinoid meta-agent 는 그 위에 올라가는 첫 번째 runtime adaptive 오케스트레이터다.

**가정:**
- Claude Code 가 주 실행 환경 (hooks, agents, memory 디렉토리 접근 가능)
- Phase 0 = 관찰 + 제안 전용. 실행 자동화 없음
- 사용 데이터 전무 상태에서 시작 (A10 원칙: 추측 기반 "패턴" 신뢰 금지)
- solo 개발, 주 25-40h 시간 예산 (Q3/Q4 spec 과 동일 제약)
- 기존 Q3/Q4 spec 의 결정은 변경하지 않음 (Phase 0 은 dotclaude-core 의존 0)

---

## 2. 사용자 원문 (User Intent Quote — 변형 금지)

> "총괄에이전트 추가. 애칭은 요시노이드.
> 특정 요청 이후에는 보통 어떤 요청을 했다. 이번에는 이 요청이 적절할 것 같다. 이런 걸 알려준다.
>
> 예를 들어 '개발이 완료되었으니 이번에 문서정리 에이전트가 정리 한번 해. 남은 later 뭐 있지?
> 이건 우리가 먼저 seb 로 끝내놓자. 이건 아무리 seb 해도 우리끼리 결정할 수 없을 것 같아. later 에 남기자.'
>
> 에이전트들이 나에게 물어볼 것들을 요시노이드에게 한번 물어본다.
> 요시노이드는 내 사용 패턴을 분석해서 자신의 지휘 능력을 키운다.
>
> 이런 아이디어로 요시노이드를 고도화하고 추가하자. 물론 이것도 seb 사용하기."

— `~/.claude/docs/later.md` ★★ yoshinoid 섹션 원문 (2026-04-10)

후속 발화 (원문 보존):
> "yoshinoid 라는 이름을 쓰는 게 비효율적이면 그냥 총괄 에이전트로 지칭해도 돼."
> "요시노이드는 나중에 확장될 가능성도 있어서 이름을 붙였어"
> "생각해봤는데 에이전트는 이름 유연성을 주지 않는 게 낫겠다 일단 최고효율을 추구해야 하니까"

→ **결론**: `yoshinoid` 고정. 확장 가능성이 있는 고유 엔티티로 취급.

---

## 3. Origin & Customization

### 3.1 Research Summary

**Researched:** 2026-04-10
**Method:** agent-skill-creation rule 적용 (5 external sources)

| # | Source | URL | 가져온 것 |
|---|---|---|---|
| S1 | Claude Code Agent Teams 공식 문서 | https://code.claude.com/docs/en/agent-teams | Agent Teams 는 병렬 작업 전용 → yoshinoid 는 single-session meta-orchestrator 로 구별 확정. Phase 2+ 에서 `TeammateIdle` / `TaskCreated` / `TaskCompleted` hooks 활용한 team lead 진화 경로 발견 |
| S2 | Claude Code Hooks Reference | https://code.claude.com/docs/en/hooks | **UserPromptSubmit hook + type "agent"** = pre-prompt 시점 subagent 호출 공식 구현체 확인. `stdout → additionalContext` 주입 메커니즘 확인. ⚠️ "UserPromptSubmit hook that spawns subagents can create infinite loops" 경고 → 방어 필수 |
| S3 | Harness (revfactory) | https://github.com/revfactory/harness | 6 architectural patterns 조사. yoshinoid = Supervisor + Expert Pool 혼합. **Harness 는 self-evolving 없음** → yoshinoid 의 unique 포인트 검증 (Harness = generator only, yoshinoid = runtime adapter) |
| S4 | agent-orchestrator-template (shintaro-sprech) | https://github.com/shintaro-sprech/agent-orchestrator-template | Coverage-based routing (90%+/60-90%/<60%), YAML manifest 기반 usage_count + success_rate, elite tier promotion 참고. yoshinoid 는 stage-based (S0/S1/S2) + A10 원칙으로 더 conservative |
| S5 | wshobson/agents + hesreallyhim/awesome-claude-code | https://github.com/wshobson/agents + https://github.com/hesreallyhim/awesome-claude-code | 182 agents + 16 orchestrators reference. critic/planner/executor 3-agent pattern = 검증된 관례 확인 |

### 3.2 이 사용자 맥락 반영 (Customizations)

1. **Single-session vs Agent Teams**: Claude Code Agent Teams 는 병렬 분산 작업용. yoshinoid 는 single-session 내 pre-prompt 판단 오케스트레이터. 두 개념을 혼용하지 않는다.
2. **Self-evolving vs Static Generator**: Harness / agent-orchestrator-template 은 정적 생성기. yoshinoid 는 Phase 1+ 에서 runtime adaptive (패턴 누적 → 자기 제안). Phase 0 에서는 static generator 와 동급이나 구조는 진화를 전제로 설계.
3. **AI Orchestration 렌즈**: 사용자 역할 = later 큐 관리 + 방향 설정 + 승인. yoshinoid 는 그 파이프라인에서 "다음 액션 제안"만 담당. 실행 자동화는 Phase 0 범위 외.
4. **Fractal 정합**: 사용자 → yoshinoid(lab) → dotclaude(flagship) → yoshinoid(meta-agent) 모두 같은 "yoshinoid" 우산. Q4 spec D6 의 fractal 포지셔닝과 직접 연결.
5. **Korean/English 이중 언어**: 본문 한국어, 식별자·파일명·코드는 영어. CLAUDE.md global rule 정합.

---

## 4. Intent Anchors (A1-A19)

Phase 2 SEB 25 loops 수렴 결과. 전체 19 anchors.

| ID | Anchor | Confidence | 비고 |
|---|---|---|---|
| A1 | yoshinoid 는 기존 에이전트들을 조율하는 meta-layer 다 — 기능 에이전트가 아니다 | strong | SEB 1 loop 수렴 |
| A2 | 사용 패턴 관찰 → 다음 제안 이 핵심 가치다 (단순 명령 실행이 아님) | strong | 사용자 원문 직접 추출 |
| A3 | 사용자 원문은 변형 없이 보존한다 | strong | hard rule |
| A4 | yoshinoid 자신의 파일 (agent, spec, brand) 은 영구 Tier 2 (사용자 직접 승인) | strong | 보안 원칙 정합 |
| A5 | Phase 0 = 관찰 + 제안. 자동 실행 없음 | strong | critic C1 반영 |
| A6 | yoshinoid 이름은 고정. 유연성 없음 | strong | 사용자 발화 직접 확정 |
| A7 | yoshinoid 를 축소·sunset 하는 방향의 제안 금지 | strong | 사용자 의지 명시 |
| A8 | escalation ladder: suggest → ask-shortened → defer-to-user → defer-to-later | strong | Phase 2 루프 수렴 |
| A9 | later.md 는 read-only 참조만. 직접 append 는 writer hook 만 | strong | 안전 원칙 |
| A10 | 실제 사용 데이터 전무 → "패턴 학습" 관련 결정은 weak/medium 신뢰만 | strong | Confidence downgrade 5회 적용 |
| A11 | Memory 파일 3개 분리: state / patterns / corrections | medium | Phase 2 수렴 |
| A12 | Writer hook 은 yoshinoid-writer.sh 단 하나. path whitelist 강제 | strong | critic C2 반영 |
| A13 | Hook recursive 방어: regex matcher + env var 2중 | strong | S2 Hooks Reference 경고 반영 |
| A14 | Phase 0 = S0 고정. 자동 stage 승격 없음 | strong | critic C3 반영 |
| A15 | Self-proposal (reports/ 경로) 은 Phase 0 에서 완전 차단 | strong | Phase 1+ 로 defer |
| A16 | UserPromptSubmit hook 은 opt-in (settings.local.json). 전역 default-on 은 Phase 0.5 | medium | 사용자 선택권 보존 |
| A17 | Harness 대비 unique = runtime adaptive. Phase 0 에서는 잠재적 차별점 | medium | A10 원칙 적용 — 데이터 없음 |
| A18 | Memory token budget = 2k (Phase 0 실측 후 조정) | medium | A10 원칙 적용 |
| A19 | yoshinoid 는 Claude Code Agent Teams team lead 로 진화 가능 (Phase 2+) | weak | 현재 데이터 0, 구조적 가능성만 |

**Confidence 등급 정의:**
- `strong`: 사용자 발화 직접 추출 또는 SEB 수렴 + critic 검토 완료
- `medium`: SEB 수렴이나 관찰 데이터 부재로 실측 검증 필요
- `weak`: 구조적 가능성, 현재 실증 근거 없음

---

## 5. 결정 사항 (D1-D7)

| # | 항목 | 결정 | 대안 (기각 이유) | Confidence | 진화 경로 |
|---|---|---|---|---|---|
| D1 | Pattern storage | 3 markdown 파일 (`yoshinoid_state.md` / `yoshinoid_patterns.md` / `yoshinoid_corrections.md`) + `later.md` read-only 참조 | sqlite DB (Phase 0 에 overkill, 의존성 추가), 단일 파일 (관심사 혼재 → 읽기 복잡) | strong | Phase 1+ 에서 sqlite 전환 검토 (multi-session race 해결) |
| D2 | 학습 방식 | Phase 0 = lookup only (기존 패턴 참조). 신규 패턴 추가는 사용자 확인 후 | 완전 자동 학습 (A10: 데이터 전무 상태에서 오토마틱 학습 = 잘못된 신뢰 축적), n-gram/embedding (Phase 1+) | strong | Phase 1 = 명시 signal 기반 semi-auto 추가, Phase 2+ = embedding 기반 |
| D3 | 실패 모드 처리 | corrections.md 에 회피 규칙 누적 (append-only, Phase 0). 학습 아님 | 자동 재시도 (Phase 0 범위 외), 30d decay (Phase 1+ 로 defer) | strong | Phase 1+ = decay + weight 조정 |
| D4 | Meta-recursive self-modification | Phase 0 = self-modification 완전 차단 (writer hook path whitelist 에서 agent 파일 차단). Phase 1+ = dry-run 2-file output | self-edit 허용 (A4: yoshinoid self-edit 영구 Tier 2, Phase 0 에서는 데이터 전무로 차단이 안전) | strong | Phase 1+ = dry-run 출력 전용 (실제 파일 수정 안 함), Phase 2+ 재검토 |
| D5 | Trigger 방식 | 3-tier: T1 explicit `@yoshinoid` / T2 UserPromptSubmit hook (opt-in) / T3 session-boundary. **Phase 0 = T1 항상 + T2 opt-in subset** | T2 default-on (부트스트랩 모순 + 무한 루프 리스크 → Phase 0.5 로 defer), T3 (post-session hook 동작 미검증 → Phase 0.5) | strong | Phase 0.5 = T3 추가, T2 전역 활성화 여부 결정 |
| D6 | Permission 동적 정책 (Stage Machine) | S0 고정 (Phase 0 전체). S1/S2 전환 조건은 Phase 0 관찰 데이터 수집 후 재결정 | Phase 0 에서 S1 진입 허용 (critic C3: 측정 순환논리 → 데이터 없이 임계값 정의 불가) | strong | Phase 1 = S0→S1 전환 조건 재결정 spec |
| D7 | Skill/Command 라우팅 | yoshinoid 내부에서 완전 흡수. 별도 hook wrapper 없음. default path (yoshinoid 미경유) 변경 없음 | 각 skill/command 에 wrapper hook 추가 (관리 복잡도 폭증, default path 오염) | strong | Phase 0 구조 유지 |

---

## 6. 설계 상세

### 6.1 파일 구조

```
~/.claude/
├── agents/
│   └── yoshinoid.md              ← 신규 (150-250 lines, Read/Grep/Glob only)
├── memory/
│   ├── yoshinoid_state.md        ← 신규
│   ├── yoshinoid_patterns.md     ← 신규
│   └── yoshinoid_corrections.md  ← 신규
├── hooks/
│   └── yoshinoid-writer.sh       ← 신규 (유일한 쓰기 주체, path whitelist)
└── settings.local.json           ← UserPromptSubmit hook opt-in entry 추가 (사용자 선택)
```

**신규 파일 요약:**
- `agents/yoshinoid.md` — meta-agent 정의. tools: Read, Grep, Glob 만 (쓰기 도구 없음)
- `memory/yoshinoid_state.md` — 설정 + 카운터 + 최근 corrections (cap 3)
- `memory/yoshinoid_patterns.md` — lookup table (trigger → suggested action, confidence, n)
- `memory/yoshinoid_corrections.md` — negative signal append-only log
- `hooks/yoshinoid-writer.sh` — 유일한 쓰기 주체

### 6.2 Trigger Flow (3-tier, Phase 0 활성 = T1 + T2 subset)

```
사용자 프롬프트
│
├─ T1: @yoshinoid 명시 ──────────────────────────────── 항상 동작
│       └─ yoshinoid subagent 직접 호출
│
├─ T2: UserPromptSubmit hook (opt-in, settings.local.json)
│       ├─ matcher: ^(?!@yoshinoid).*  (recursion 방지 regex)
│       ├─ env guard: YOSHINOID_HOOK_DEPTH=1 (2중 방어)
│       ├─ timeout: 30s
│       ├─ yoshinoid 판단 → additionalContext 주입 또는 통과
│       └─ ⚠️ 무한 루프 방어 필수 (S2 공식 경고)
│
└─ T3: session-boundary light summary ───────────────── Phase 0.5 로 defer
        (post-session hook 동작 미검증)
```

**T2 opt-in 방법 (settings.local.json 예시):**
```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "type": "agent",
        "subagent_type": "yoshinoid",
        "matcher": "^(?!@yoshinoid)",
        "env": {
          "YOSHINOID_HOOK_DEPTH": "1"
        },
        "timeout": 30
      }
    ]
  }
}
```

> 시크릿·실제 인증 정보는 기록 금지. 위 설정에 API 키 포함 불가.

### 6.3 yoshinoid Agent 구조 (agents/yoshinoid.md 설계)

**Frontmatter:**
```yaml
name: yoshinoid
description: |
  Meta-orchestrator for yoshinoid lab. Observes usage patterns and suggests
  next actions. Read-only tools only. Phase 0: S0 fixed, no auto-execution.
  Use when: user asks @yoshinoid directly, OR UserPromptSubmit hook activates.
tools:
  - Read
  - Grep
  - Glob
model: claude-sonnet-4-6
```

**본문 섹션 목록:**
1. **Identity** — fractal 포지셔닝 2-3 문장 (사용자 → lab → flagship → meta-agent)
2. **Hard Rules** — no self-edit / Tier 2 영구 / dry-run Phase 1+ / no recursive yoshinoid call
3. **Trigger Model** — T1/T2/T3 설명 + Phase 0 활성 범위
4. **Escalation Ladder** — suggest → ask-shortened → defer-to-user → defer-to-later
5. **Stage Machine** — S0 고정 (Phase 0). S1/S2 는 placeholder only
6. **Memory Read Protocol** — 2k token budget. 초과 시 state 우선, patterns 최대 10행, corrections 최대 5행
7. **Output Templates** — ko 사용자 응답 / en 식별자
8. **Off-switch** — `yoshinoid_state.md` 의 `enabled: false` 로 즉시 비활성화
9. **Known Limitations** — A10 원칙 명시 (관찰 데이터 전무)

### 6.4 Memory Files Schema

#### yoshinoid_state.md
```markdown
# yoshinoid State

## Config
enabled: true
stage: S0
sleep_until: null

## Counters
suggestions_total: 0
suggestions_accepted: 0
corrections_total: 0
last_updated: YYYY-MM-DD

## Recent Corrections (cap: 3)
<!-- append-only via yoshinoid-writer.sh -->

## Session Toggle
<!-- session-end toggle: Phase 0.5 -->
```

#### yoshinoid_patterns.md
```markdown
# yoshinoid Patterns (lookup table)

Phase 0: lookup only. 신규 추가 = 사용자 확인 후 writer hook.

## Pattern Table (top-10, Phase 0 = 사용자 원문 기반 seed 5개)

| trigger_event | suggested_action | confidence | n |
|---|---|---|---|
| "개발/구현/feature 완료" 키워드 감지 | 문서정리 에이전트 호출 제안 + `남은 later 조회` | medium (seed) | 0 |
| `later.md` active 항목 ≥ 5 | later 정리·우선순위 조정 제안 | medium (seed) | 0 |
| spec 저장 직후 | 관련 memory 파일 업데이트 필요성 확인 | medium (seed) | 0 |
| `research.md` stale entry (3 months+) 감지 | `/research --refresh` 제안 | medium (seed) | 0 |
| 세션 중 "아이디어 있는데/추가하자/괜찮겠다" 3회+ | 아이디어 매니저 lens 호출 제안 + 중복 체크 | weak (seed) | 0 |

**Seed 근거**: 사용자 원문 (Section 2) — "개발이 완료되었으니 이번에
문서정리 에이전트가 정리 한번 해. 남은 later 뭐 있지?" 와 2026-04-10 세션에서
관찰된 아이디어 폭발 패턴 기반. 관찰 데이터 부재 (A10) 원칙 위반 아님 —
사용자 명시 원문 + 구조적 trigger 로만 구성. 실사용 counter 쌓이면 confidence 진화.
```

#### yoshinoid_corrections.md
```markdown
# yoshinoid Corrections (append-only)

Phase 0: append-only. 30d decay = Phase 1+.

<!-- FORMAT: date | trigger | wrong_suggestion | correction_note -->
```

### 6.5 Writer Hook Script (hooks/yoshinoid-writer.sh)

**역할:** memory 파일에 대한 유일한 쓰기 주체.

**Path whitelist (쓰기 허용):**
- `~/.claude/memory/yoshinoid_state.md` — counter delta, enabled toggle
- `~/.claude/memory/yoshinoid_patterns.md` — pattern append (사용자 확인 후)
- `~/.claude/memory/yoshinoid_corrections.md` — correction append

**Path blacklist (쓰기 거부):**
- `~/.claude/agents/yoshinoid.md` — agent self-edit 불가 (A4)
- `~/.claude/memory/reports/` — self-proposal Phase 0 완전 차단 (A15)
- `~/.claude/settings*.json` — settings 보호
- spec 파일들 — 별도 spec-agent 관할

**Schema whitelist (내용 검증):**
- counter delta: `+N` 형식만
- enabled toggle: `true` / `false` 만
- pattern append: `| trigger | action | confidence | n |` 행 형식만
- correction append: `<!-- date | trigger | wrong | note -->` 형식만

**Tier 1 auto-commit 지원:** 패턴 테이블 수정 시 git commit 자동 실행.

### 6.6 Permission Boundary — Stage Machine

| Stage | 활성 Phase | 권한 | 전환 조건 |
|---|---|---|---|
| S0 | Phase 0 (고정) | Read-only memory, suggest-only output | Phase 0 완료 후 재결정 |
| S1 | Phase 1 | S0 + memory write (via writer hook) | [Phase 0 관찰 데이터 기반 재결정] |
| S2 | Phase 2 | S1 + dry-run self-proposal | [Phase 1 관찰 데이터 기반 재결정] |

**영구 예외 (S2 에서도 Tier 2 유지):**
- yoshinoid self-edit (agent 파일, spec 파일)
- brand 파일 (`~/.claude/docs/`, `~/.claude/rules/`)
- 모든 spec 파일 (`*/specs/*.md`)

### 6.7 Skill/Command Routing (D7)

yoshinoid 가 호출되면 내부에서 skill/command meta-router 역할을 수행한다.

```
@yoshinoid 호출
└── yoshinoid 내부 판단
    ├── "다음에 /commit 하세요" → suggest (실행 안 함)
    ├── "seb 로 먼저 끝낼 수 있어요" → suggest
    ├── "later 에 남기는 게 좋아요" → suggest + defer-to-later
    └── "판단 불가" → defer-to-user
```

**설계 원칙:**
- hook wrapper 별도 없음 (D7)
- default path (yoshinoid 미경유) 변경 없음 → 기존 skill/command 동작 보장
- yoshinoid 는 제안만, 실행 트리거 없음 (Phase 0)

---

## 7. Phase 0 Deliverables & Done Criteria

### 7.1 신규 파일 목록 (5개 필수 + 1개 선택)

| 파일 | 필수 여부 | 비고 |
|---|---|---|
| `~/.claude/agents/yoshinoid.md` | 필수 | 150-250 lines |
| `~/.claude/memory/yoshinoid_state.md` | 필수 | 초기값으로 생성 |
| `~/.claude/memory/yoshinoid_patterns.md` | 필수 | 빈 테이블로 생성 |
| `~/.claude/memory/yoshinoid_corrections.md` | 필수 | 빈 로그로 생성 |
| `~/.claude/hooks/yoshinoid-writer.sh` | 필수 | path whitelist 포함 |
| `~/.claude/settings.local.json` T2 entry | 선택 | 사용자 opt-in |

### 7.2 Phase 0 성공 기준

**Track 2 (yoshinoid kernel agent-side)**:

| # | 기준 | 확인 방법 |
|---|---|---|
| C1 | `@yoshinoid` explicit 호출 정상 응답 3회 이상 | 실제 호출 기록 (`yoshinoid_state.md` suggestions_total ≥ 3) |
| C2 | `yoshinoid_state.md` 제안 카운터 ≥ 5건 기록 | `cat ~/.claude/memory/yoshinoid_state.md` 확인 |
| C3 | `yoshinoid_corrections.md` 기록 메커니즘 동작 확인 (≥ 1건) | correction 1건 이상 append 후 파일 확인 |
| C4 | writer hook path whitelist 동작 검증 | agent 파일 쓰기 시도 → 거부 확인 |
| C5 | Origin 섹션이 이 spec 과 `agents/yoshinoid.md` 양쪽에 존재 | `grep -l "Origin" ~/.claude/agents/yoshinoid.md` |
| C6 (선택) | UserPromptSubmit hook opt-in 활성화 후 pre-prompt buffer 최소 1회 실증 | T2 trigger log 확인 |

**Track 1 (dotclaude-core thin slice, v2.1 추가, 2026-04-11)**:

| # | 기준 | 확인 방법 |
|---|---|---|
| C7a | **(Phase 0 범위)** Usage extension Tier 1 auto-commit **mechanism 증명** — tmp git repo E2E 1회 | `pytest dotclaude-core/tests/e2e/test_usage_slice.py -v` green. assertion: `dotclaude/evolve/<date>` branch + commit 1 + Tier 0 reports/ + memory patch in branch |
| C7b | **(Phase 0.5 범위, deferred)** Production target 에서 Tier 1 auto-commit 1회 | logbook repo 또는 `dotclaude-core/.local/` 에서 실 사용 1회. **Trigger: C7a green + C1 ≥ 3 달성 후 7일 내 Phase 0.5 진입. 미진입 시 handoff.md 자동 블로커 등록** (critic P0-a). |
| C8 | dotclaude-core README v1 작성 | `c:/Users/jeong/projects/yoshinoid/dotclaude-suite/dotclaude-core/README.md` 존재 + Usage extension demo 섹션 + yoshinoid kernel 연결 설명 grep 검증 |
| C9 | 단위 테스트 커버리지 75% 이상 (전체) + 핵심 3 모듈 95% 이상 | `pytest --cov=dotclaude_core --cov-fail-under=75` green. 핵심 3 (`contracts/classify_path/write_gateway`) 별도 95% 강제 |

**Cross-track consistency (v2.1 추가)**:

| # | 기준 | 확인 방법 |
|---|---|---|
| C10 | §16 family snapshot drift 감지 작동 | `sha256sum` of Phase 0 spec §16 block == `yoshinoid_state.md` 기록 값. mismatch 시 verifier 가 즉시 세션 중단 + handoff.md 알림 |
| C11 | "plugin / Plugin" 단어 잔존 0 (dotclaude-core / dotclaude-usage / yoshinoid-writer.sh) | `rg -w 'plugin\|Plugin' ...` allowlist 적용 후 0건. allowlist: `parsers/plugins.py` (기존), `extension.toml` (manifest), Q3 spec 원문 인용 |

### 7.3 사용자 가치 증명

Phase 0 완료 시 사용자가 다음 1줄 reflection 작성 (retrospective 형태):

> "yoshinoid 가 실제로 인지 부하를 줄였는가?" — Y/N + 1줄 이유

이 reflection 이 없으면 Phase 0 완료 선언 불가.

---

## 8. 범위 경계

### 포함 (Phase 0)
- T1 explicit `@yoshinoid` 호출
- T2 UserPromptSubmit hook (opt-in 방식)
- memory 3파일 초기 구조 생성 및 read
- yoshinoid-writer.sh path whitelist 쓰기
- S0 고정 permission
- suggest-only output (실행 자동화 없음)
- correction append-only 메커니즘

### 미포함 (Phase 0) — defer 이유 명시

| 항목 | defer 이유 | 예정 Phase |
|---|---|---|
| T2 전역 활성화 (default-on) | 부트스트랩 모순 + 무한 루프 리스크 미검증 | Phase 0.5 |
| T3 session-boundary light summary | post-session hook 동작 실측 전 | Phase 0.5 |
| S1/S2 stage 전환 | Phase 0 관찰 데이터 없이 임계값 정의 불가 (A10) | Phase 1 |
| Self-proposal dry-run (reports/ 경로) | Phase 0 = 관찰 전용, 자기 제안은 데이터 축적 후 | Phase 1 |
| Supervisor 모드 | Agent Teams 통합 필요 (Phase 2+ 진화) | Phase 2+ |
| Project-local later queue 통합 | dotclaude-core Later DB 구현 선행 필요 (Q3 spec) | Phase 2+ |
| Multi-machine state 동기화 | Phase 0 last-write-wins 수용 | Phase 1+ |
| 자동 Learning (n-gram → embedding → LLM) | A10: 데이터 전무 상태에서 구현은 premature | Phase 1+ |
| Team lead 진화 (Claude Code Agent Teams) | A19: 구조적 가능성만, 현재 근거 없음 | Phase 2+ |

> 범위 추가 시 이 섹션을 먼저 업데이트하고 변경 이력에 기록할 것.

---

## 9. Cross-Spec Impact

### Q3 spec (2026-04-10-dotclaude-plugin-nucleus-architecture.md)
- **수정 불필요**: Phase 0 는 dotclaude-core 의존 0. Q3 spec 의 결정에 영향 없음.
- **향후 연결점**: Phase 2+ 에서 yoshinoid 가 Later DB (`later_items` 테이블) 를 직접 읽을 때 Q3 Later DB API 를 통해야 함 → 그때 Q3 spec UPDATE 필요.

### Q4 spec (2026-04-10-dotclaude-yoshinoid-flagship-alignment.md)
- **주석 추가 제안** (선택): Q4 spec 의 Tier 제약 표에 다음 주석 1줄 추가를 권고함:
  ```
  Note: yoshinoid meta-agent self-edit → scope=personal, 영구 Tier 2 (2026-04-10-yoshinoid-meta-agent-phase-0 D4/A4 참조)
  ```
- 이 spec 단독으로 Q4 spec 을 수정하지 않음. 사용자가 Q4 spec UPDATE 를 별도로 진행해야 함.

---

## 10. 리스크 & 완화

| ID | 리스크 | 영향 | 완화 방안 | 출처 |
|---|---|---|---|---|
| R1 | 부트스트랩 모순: T2 default-on 시 yoshinoid 가 자신을 분석하는 루프 | 중 | T2 = opt-in subset only (Phase 0). Default-on 은 Phase 0.5 로 defer | critic C1 |
| R2 | dry-run 우회: writer hook 이 agent 파일 덮어쓰기 | 높 | writer script path whitelist 엄격 적용. agent 파일 = blacklist | critic C2 |
| R3 | 측정 순환논리: 임계값을 데이터 없이 정의 | 중 | Phase 0 = S0 고정. 임계값은 Phase 0 관찰 데이터 수집 후 재결정 | critic C3 |
| R4 | 무한 루프: hook 이 yoshinoid 를 재귀 호출 | 높 | matcher regex `^(?!@yoshinoid)` + `YOSHINOID_HOOK_DEPTH=1` env var 2중 방어 | S2 공식 경고 반영 |
| R5 | "잊혀짐": Phase 0.5 이전에 yoshinoid 가 비활성 | 낮 | Phase 0.5 discovery notice 메커니즘 (T3 서브셋으로 구현) | W3 warning 반영 |
| R6 | Multi-session race condition: 동시 쓰기로 memory 파일 충돌 | 낮 | Phase 0 = last-write-wins 수용. Phase 1+ 에서 파일 락 또는 sqlite 전환 | R6 |
| R7 | Token budget overrun: memory 읽기 2k 초과 | 낮 | Phase 0 실측 후 조정. 초과 시 state 우선, patterns 10행, corrections 5행 순으로 트리밍 | A18 medium |
| R8 | Hook API 버전 호환성: Claude Code hook spec 변경 | 낮-중 | 공식 문서 변경 모니터링. hook 비활성화로 fallback (T1 만으로도 core 기능 유지) | S2 research |

---

## 11. Known Limitations (솔직한 한계)

1. **A10 원칙 — 관찰 데이터 전무**: 현재 모든 "패턴 학습" 관련 결정(D2, D3, D6)은 weak/medium confidence. `yoshinoid_patterns.md` 초기 테이블은 비어있으며, 이것이 정직한 출발점이다.

2. **Phase 0 = S0 고정으로 진화 경로가 Phase 1 진입에 의존**: T2 opt-in 활성화 없이는 관찰 데이터 축적 속도가 매우 느릴 수 있다. "사용자가 T2 opt-in 을 실제로 켜는가"가 Phase 0 성공의 숨겨진 전제조건.

3. **Hook 기반 pre-prompt 의 Claude Code API 의존성**: `UserPromptSubmit` hook 스펙이 Claude Code 버전 업에서 변경될 수 있다. T1 explicit 호출은 이 의존성이 없으므로, T1 만으로도 core 기능은 유지된다.

4. **Harness 대비 Phase 0 에서 차별점 미실증**: Harness 는 static generator. yoshinoid 의 runtime adaptive 장점은 Phase 1+ 에서 패턴 누적 후에야 실증된다. Phase 0 에서는 Harness 와 기능적으로 유사한 수준.

5. **Self-evolving 은 Phase 0 에서 잠재적 약속**: 이 spec 의 가장 큰 가정은 "데이터가 쌓이면 self-evolving 이 가능하다"이다. Phase 0 완료 후 사용자 reflection (7.3) 이 이 가정을 검증하는 첫 번째 데이터포인트가 된다.

---

## 12. 미결 질문

| # | 질문 | 담당 | 기한 |
|---|---|---|---|
| Q1 | T2 opt-in 을 Phase 0 기간 중 실제로 활성화할 것인가? | 사용자 | Phase 0 시작 후 1주 |
| Q2 | `yoshinoid_patterns.md` 초기 수동 입력 패턴 1-3개 작성 의향? (bootstrap 데이터) | 사용자 | Phase 0 시작 후 |
| Q3 | Memory token budget 2k 가 실측에서 충분한가? | 사용자 + yoshinoid | C2 기준 달성 후 |
| Q4 | Q4 spec Tier 제약 표 주석 추가를 별도 UPDATE 로 진행할 것인가? | 사용자 | 선택적 |
| Q5 | Phase 0.5 (T3 + T2 default-on) 를 Phase 0 완료 직후 시작할 것인가, 별도 spec 으로 분리할 것인가? | 사용자 | Phase 0 완료 후 |

---

## 13. Deferred Items → later.md (별도 append 대상)

아래 8개 항목은 Phase 0 완료 후 `~/.claude/docs/later.md` 에 `/later` 로 append 권장:

1. Claude Code post-session hook 실제 동작 관찰 (Phase 0.5)
2. Acceptance metric 키워드 분류 세부 설계 (Phase 1)
3. Token budget 2k 실측 조정 (Phase 0 이후)
4. S0/S1/S2 임계값 재결정 spec (Phase 1 시작 전)
5. Project-local later queue 통합 (Q3 Later DB 구현 후)
6. yoshinoid → Claude Code Agent Teams team lead 진화 경로 (Phase 2+)
7. hook UserPromptSubmit 무한 루프 방어 E2E 테스트
8. `yoshinoid-self-writer.sh` 분리 (Phase 1+, self-proposal dry-run 구현)

> 이 spec 에서 직접 append 하지 않음. 사용자가 `/later` 명령으로 추가.

---

## 14. 검증 기준

`/verify` 에서 확인할 항목:

- [ ] `~/.claude/agents/yoshinoid.md` 존재 확인: `ls ~/.claude/agents/yoshinoid.md`
- [ ] `yoshinoid.md` frontmatter 에 tools = [Read, Grep, Glob] 만 포함 (쓰기 도구 없음): `grep -A5 "tools:" ~/.claude/agents/yoshinoid.md`
- [ ] memory 3파일 존재 확인: `ls ~/.claude/memory/yoshinoid_{state,patterns,corrections}.md`
- [ ] writer hook 존재 + 실행 권한: `ls -l ~/.claude/hooks/yoshinoid-writer.sh`
- [ ] writer hook path whitelist 적용: `cat ~/.claude/hooks/yoshinoid-writer.sh | grep whitelist`
- [ ] `@yoshinoid` 호출 3회 이상 정상 응답: `grep suggestions_total ~/.claude/memory/yoshinoid_state.md` (값 ≥ 3)
- [ ] corrections 메커니즘 동작: `cat ~/.claude/memory/yoshinoid_corrections.md` (≥ 1행)
- [ ] Origin 섹션 양쪽 존재: `grep "Origin" ~/.claude/agents/yoshinoid.md`
- [ ] 사용자 Phase 0 reflection 작성 완료 (7.3 기준)

---

## 15. 변경 이력

| 날짜 | 버전 | 변경 | 이유 |
|---|---|---|---|
| 2026-04-10 | 1 | 초안 생성 (Phase 0 spec) | SEB 25 loops + critic CONDITIONAL APPROVAL + internet research 5 sources 통합 |
| 2026-04-11 | 2 | §16 Family Kernel Reframe addendum | Meta-Agent Family 통합 SEB Round 1 (14 loops, Confidence downgrade 적용). 기존 A1-A19/D1-D7 변경 없음. Lens namespace reservation + cross-agent communication 규칙 + Phase 순서 제안 추가. |
| 2026-04-11 | 2.1 | §7.2 Track 1 Done criteria 추가 (C7a/C7b/C8/C9 + C10/C11) | Phase 0 implementation plan v2 (planner Round 2 + critic Round 2 CONDITIONAL APPROVAL) 의 Track 1 (dotclaude-core thin slice) 부분이 §7.2 에서 누락되어 있어 추가. C7a (tmp E2E mechanism) / C7b (production deferred to Phase 0.5, 7일 trigger) / C10 (§16 family sha256 drift) / C11 (Plugin→Extension naming 잔존 0). 아키텍처 결정 변화 없음, criteria 명세화. |

---

## 16. Family Kernel Reframe (v2, 2026-04-10 SEB Round 1)

### 16.1 Reframe 요약

yoshinoid 는 **단일 meta-agent 가 아니라 meta-agent family 의 kernel** 이다.
Phase 0 spec v1 의 설계는 kernel 로 그대로 유효하며, 이 섹션은 family 맥락과
lens reservation 만 추가한다. **A1-A19 / D1-D7 / 파일 구조 / Stage Machine
변경 없음.**

### 16.2 Family 구성 (4 lens, 원문 보존)

시간축 4분할 mapping:

| # | Lens | 사용자 질문 | 시간축 | verb | 원문 출처 |
|---|---|---|---|---|---|
| L0 | **yoshinoid** (kernel) | "지금 뭐 할까?" | present-internal | **orchestrate / route** | Phase 0 spec §2 |
| L1 | **비서 에이전트** | "누가 나한테 뭐 시켰어?" | present-external | **receive** | `~/.claude/docs/ideas.md` Active |
| L2 | **커리어 관리 에이전트** | "내가 뭐 했어?" | past | **chronicle** | `~/.claude/docs/ideas.md` Active |
| L3 | **아이디어 매니저 에이전트** | "내가 뭐 떠올렸어?" | future-seeds | **capture** | `~/.claude/docs/ideas.md` Active |

**책임 중복 매트릭스**: 4 질문 × 4 lens = 1:1 매핑, 중복 0.

### 16.3 Kernel 책임 (공통 인프라 7 컴포넌트, 기존 Phase 0 spec 계승)

1. **Pattern storage** — `yoshinoid_patterns.md` (lookup table, lens seed pattern 포함)
2. **Trigger model** — T1 explicit / T2 UserPromptSubmit / T3 session-boundary
3. **Escalation ladder** — suggest → ask-shortened → defer-to-user → defer-to-later
4. **Writer hook monopoly** — `yoshinoid-writer.sh` 단일 쓰기 주체 (A12 계승)
5. **Memory schema** — `yoshinoid_{state,patterns,corrections}.md` + lens namespace 확장
6. **Permission stage machine** — S0/S1/S2 (Phase 0 = S0 고정, A14 계승)
7. **Off-switch** — `yoshinoid_state.md.enabled = false` (family 전체 비활성)

**Lens 는 위 7 컴포넌트를 소유하지 않는다** — 전부 kernel 경유.

### 16.4 Lens 책임 (specialization only)

각 lens 는 다음 3가지만 소유:
- **Domain reader** (lens 고유 데이터 소스 읽기)
- **Specialized suggestion template** (lens 도메인 언어로 출력)
- **Own memory namespace** (`<lens>_*.md`, read-only for kernel/other lens)

Lens 는 다음을 **소유하지 않는다**: writer hook, pattern storage, trigger model,
stage machine, off-switch. 이 모두 kernel 에서 주입.

### 16.5 Cross-Agent Communication — Kernel-Mediated State Passing

- **Lens → Lens direct call 금지** (import / subagent spawn 모두 차단)
- 통신 경로: Lens A → kernel memory 에 signal write → kernel 이 다음 호출 시 read → lens B 제안 surface → 사용자 승인 → lens B 명시 호출
- 이유: lens 독립성 + recursion 리스크 회피 + A4 상속 게이트 강제
- Confidence: **medium** (kernel-mediated > pub/sub 이론적 비교만, 실사용 0)

> **레이어 주의 (critic F1)**: 이 규칙은 **meta-agent lens 레이어에만 적용**된다.
> `dotclaude` plug-in 레이어의 `event_bus` (Q3 plug-in nucleus spec §4) 는 다른
> 추상 수준 (plug-in 간 런타임 이벤트) 이며 pub/sub 허용이 유지된다. 두 레이어는
> 명칭이 유사할 뿐 충돌하지 않는다.

### 16.6 Recursion Safety (family 확장)

Phase 0 spec R4 (hook 재귀 방어) 를 family 전체로 확장:

- `YOSHINOID_HOOK_DEPTH=1` → `FAMILY_HOOK_DEPTH=1` 로 확장 (lens 자체 env guard)
- Lens → Lens 경로는 반드시 사용자 경유 (DAG 강제)
- Kernel 이 lens 를 hook 자동 spawn 금지 — 항상 suggest 형태
- Lens 의 suggest 도 상위 kernel 에 전달 → kernel 이 top-1 집계 후 사용자에게 surface

### 16.7 Lens Namespace Reservation (Phase 0 spec §6.1 확장)

Phase 0 spec 의 memory 파일 구조는 유지하되, lens namespace 를 **예약만** 한다
(실제 파일 생성은 각 lens 구현 Phase 에서).

```
~/.claude/memory/
├── yoshinoid_state.md          ← Phase 0 (존재)
├── yoshinoid_patterns.md       ← Phase 0 (존재)
├── yoshinoid_corrections.md    ← Phase 0 (존재)
├── secretary_*.md              ← [RESERVED] Phase 2+ (out-of-process lens)
├── career_*.md                 ← [RESERVED] Phase 1 (공유 가능성 ★)
└── ideamgr_*.md                ← [RESERVED] Phase 0.5 (이번 세션 use case)
```

Writer hook path whitelist 도 동일하게 namespace **예약만** (실제 활성화는 lens 구현 시):

```bash
# yoshinoid-writer.sh (Phase 0 = yoshinoid_* 만 활성)
WHITELIST=(
  "~/.claude/memory/yoshinoid_state.md"
  "~/.claude/memory/yoshinoid_patterns.md"
  "~/.claude/memory/yoshinoid_corrections.md"
  # RESERVED (비활성, lens 구현 시 uncomment):
  # "~/.claude/memory/secretary_*.md"
  # "~/.claude/memory/career_*.md"
  # "~/.claude/memory/ideamgr_*.md"
)
```

### 16.8 Phase 순서 재정의 (Confidence: low — 개인 우선순위 기반)

| Phase | 범위 | 근거 |
|---|---|---|
| **Phase 0** | Kernel only (기존 spec v1 그대로) | 진입점 — 변경 없음 |
| **Phase 0.5** | **Idea-manager lens** (첫 lens) | 이번 2026-04-10 세션이 live use case 증명. 구현 범위 최소 (keyword sniffer + ideas.md draft append) |
| **Phase 1** | **Career lens** | 공유·제품화 가능성 ★, identity vision `Showpiece-Driven` 축 정합 |
| **Phase 2+** | **Secretary lens** | out-of-process 필수 (Claude Code 세션 수명 밖), 가장 무거움. dotclaude-core Later DB 구현 후 가능 |

**Confidence = low**: 이 순서는 Phase 0 spec §11 의 "사용 데이터 전무" 위에
올라간 추측. 실제 순서는 Phase 0 reflection (§7.3) + 각 lens 의 ideas.md
상태 갱신 후 재결정. 이 §16.8 은 **권장이지 commit 아님**.

### 16.9 Family Evolution Path — 새 lens 추가 5-step

A4 영구 Tier 2 상속으로 새 lens 추가는 사용자 직접 승인 필수:

1. `/idea` 로 ideas.md Active 등록
2. SEB 경유 family 정합성 확인 (이 §16 매트릭스와 충돌 검토)
3. `/spec` 으로 lens spec 생성 (kernel spec 상속)
4. Kernel `yoshinoid_patterns.md` 에 trigger seed 행 추가 (writer hook 경유)
5. `yoshinoid-writer.sh` path whitelist 에 lens memory namespace 활성화

이 5-step 자체가 lens 폭발 방지 자동 게이트다.

### 16.10 Family-specific Risks (R-F1 ~ R-F4)

| ID | 리스크 | 완화 | Confidence |
|---|---|---|---|
| R-F1 | 4 lens 동시 suggest 로 사용자 인지 부하 증가 | Kernel 이 top-1 집계, 동시 surface 금지 | medium |
| R-F2 | Lens 간 memory 파일 충돌 | Per-lens namespace + single writer (§16.7) | medium |
| R-F3 | Secretary out-of-process 로 family 응집력 약화 | Kernel 이 secretary memory read-only 참조. Secretary 는 "family 의 out-of-process lens" 로 명시 | medium |
| R-F4 | Lens 개념 확장으로 자원 분산·번아웃 | 16.8 Phase 순서 준수 + 1-2 round SEB HARD 제약 family 확장 결정에도 적용 | medium |

### 16.11 Known Limitations (v2 추가)

1. **모든 family 관련 결정의 confidence 하한선 = medium** (A10 원칙 계승).
   "4-way 책임 분할이 optimal" 같은 주장은 medium, "Phase 순서" 는 low.
2. **Lens 실제 구현 없이 결정된 구조** — 첫 lens (idea-manager) 구현 시 이 §16 매트릭스 수정 가능성 있음.
3. **A10 + A4 이중 상속**: family 확장이 느려짐. 이는 의도된 보수성 (폭발 방지).

### 16.12 Cross-Spec Impact (v2)

| Spec | 영향 | 변경 유형 | 변경 이력 append 필요? |
|---|---|---|---|
| Q3 plug-in nucleus | **없음** | Phase 0 spec 과 동일하게 Phase 2+ 연결점만 | ❌ 불필요 |
| Q4 flagship alignment | **필수 (disambiguation)** — `yoshinoid` 가 Q4 §4 에서는 identity-layer (브랜드/레포 계층), §16 에서는 meta-agent kernel 로 이중 사용됨. 혼동 방지 주석 필수 (critic F2 격상) | Q4 §4 끝에 disambiguation note 추가: `"yoshinoid" scope = {identity-layer (Q4 §4), meta-agent-kernel (Phase 0 spec §16)}. 두 스코프는 fractal 정합이지만 참조 시 구분 필요.` | ✅ 필수 (본 patch 와 동시 처리) |
| Phase 0 spec (self) | 이 §16 추가 + §15 변경 이력 1행 | v2 reframe addendum | ✅ 본 patch |

Q3 spec 수정 불필요 이유: Phase 0 spec v1 §9 에서 "Q3 Later DB 연결은 Phase 2+" 로 defer 했고, family reframe 이 그 시점을 앞당기지 않음.

### 16.13 Deferred (family-level, later.md 이동 대상)

Round 1 Loop 중 peripheral 로 분류된 항목 6개 → `~/.claude/docs/later.md`
`## Deferred (self-evolver)` 에 `[Deferred] Meta-Agent Family SEB (2026-04-11)` 로 append.

1. Secretary out-of-process 아키텍처 상세 (언어/스케줄러)
2. Career lens 의 truth source (git history vs Claude tasks/)
3. Idea-manager de-duplication 유사도 threshold
4. Family 내부 verb 컨벤션 API 명세
5. Lens 별 memory token budget
6. Kernel 이 top-1 suggest 집계 시 tie-breaker 규칙

### 16.14 Confidence Downgrade Log (A10 증명)

Round 1 중 high 유혹 → medium/low downgrade 된 앵커:

| 앵커 | 강등 후 | 근거 |
|---|---|---|
| kernel-lens split 이 optimal | medium | 실사용 데이터 0, 구조적 추론만 |
| 4 verb 완전 구분 | medium | 사용 중 책임 누수 미검증 |
| secretary out-of-process 필수 | medium | 문서 기반, 실험 0 |
| Phase 순서 0→0.5→1→2 | **low** | 개인 우선순위 기반 |
| family 인지 부하 리스크 | medium | 실관찰 0 |
| kernel-mediated > pub/sub | medium | 이론 비교만 |
| evolution path 5-step | medium | 첫 lens 추가 시 변경 가능성 |

High 유지 (사용자 원문 / 하드 제약 직결):
- yoshinoid = kernel (사용자 발화)
- 4 lens 원문 보존
- A4 영구 Tier 2 상속
- Phase 0 = S0 고정 (Phase 0 spec D6)
- Lens → Lens direct call 금지 (구조적 안전)

### 16.15 SEB Round 1 Trace Summary

- **Round 수**: 1 (HARD 제약 범위 내)
- **Loop 수**: 14 (base 7 + meta-agent-family preset 7)
- **Novel insight rate**: 14/14 (Loop 10 만 partial — verb rename)
- **Consecutive empty**: 0
- **수렴 판정**: Round 1 종료 시점에 모든 preset angle 소진 + 책임 매트릭스 / 공통 인프라 / trigger model / evolution path / Phase 순서 전부 도출. Round 2 불필요.
- **Deferred 수**: 6 (peripheral, later.md 이동)
- **Confidence downgrade**: 7 앵커
