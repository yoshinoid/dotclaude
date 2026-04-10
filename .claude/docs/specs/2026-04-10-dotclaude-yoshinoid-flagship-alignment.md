---
title: dotclaude ↔ yoshinoid Flagship Alignment (Q4 수렴)
date: 2026-04-10
status: approved
version: 1
source: self-evolver-2026-04-10-q4 (24 loops, 20 insights, 20 decisions, 12 alternatives)
anchor_ref: user_dotclaude_q4_yoshinoid_flagship_intent_anchor.md
q3_spec_ref: 2026-04-10-dotclaude-plugin-nucleus-architecture.md
---

# Spec: dotclaude ↔ yoshinoid Flagship Alignment (Q4 수렴)

## 1. 목표

**한 줄 요약:** dotclaude 를 yoshinoid 의 flagship 이자 엔진으로 확립하고, Q3 Plug-in Nucleus 위에 yoshinoid 랩 전략·운영이 어떻게 맞물리는지를 결정한다.

**동기:**

Q3 에서 dotclaude 의 핵심 아키텍처(Plug-in Nucleus, EvolvePlugin, Tier 시스템, Later DB)가 확정됐다. Q4 는 그 다음 자연스러운 질문에 답한다:

> "dotclaude 라는 Claude Code setup 엔진이 yoshinoid 에서 어떤 역할을 해야 하는가?"

같은 "evolve" 동사가 dotclaude 스케일(Claude Code setup 진화)과 yoshinoid 스케일에서 fractal 하게 작동한다. 이 fractal 포지셔닝을 구조화하고, `dotclaude-core` 의 yoshinoid 공용화 시점·방식, `dotclaude.self` scope 확장, 회사 관계 3-layer, 지속 가능 운영 모델을 결정한다.

**전제 (Q3 spec 으로부터 불변):**
- Python 3.11+ 런타임, Claude Code 가 주 실행 환경
- 5-layer 아키텍처 (dotclaude-core / EvolvePlugin / Plug-ins / Integration / Server)
- Trust Tier 시스템 (0/1/2/3)
- Later DB (`later_items` 테이블)
- 주 25-40h 시간 예산, solo 개발 (🐝 Tribe 는 Phase 2)
- self-evolver 역할: spec-only (코드 구현 없음)

## 2. 범위 경계

### 포함
- dotclaude ↔ yoshinoid 관계 정의 (flagship + engine)
- yoshinoid 메타 레포 구조 설계
- Fractal 포지셔닝 (5층 evolving)
- `dotclaude-core` yoshinoid 공용화 타이밍 (extract-after-two-uses 룰)
- `dotclaude.self` scope 확장 설계 (`personal / project / yoshinoid`)
- Evolution Timeline (Phase 0/1/2/3), 증거 중심 완료조건
- Sustainability 모델 (비대칭 배분 + 주간 ritual)
- 회사 관계 3-layer (공개 / 사내 fork / 격리)
- Governance 단계별 계획 (현재 체크리스트 → Phase 1+ 공식화)
- 두 번째 yoshinoid 프로젝트 구체 시나리오 (코드 포함)
- 20 Key Decisions + 12 Rejected Alternatives

### 미포함
- 두 번째 yoshinoid 프로젝트 구체 아이디어 (이유: ideas 메커니즘으로 위임 — blind guess 금지)
- 사내 공유 구체 채널 (이유: 사용자 회사 환경 관찰 데이터 부재)
- 도메인 구매 (이유: yoshinoid umbrella LATER 유지)
- doctrine / publication rhythm 세부 (이유: Phase 3 위임)
- `dotclaude-core` 실제 공용화 구현 코드 (이유: spec-only)
- `later_items` schema scope 컬럼 추가 (이유: later.md deferred — Phase 1→2 전환 시점)

> 범위 추가 시 이 섹션을 먼저 업데이트하고 변경 이력에 기록할 것.

## 3. 핵심 렌즈 — dotclaude = yoshinoid Flagship + Engine

Q3 에서 dotclaude 는 "later 파이프라인 AI 오케스트레이터"로 정의됐다. Q4 에서 그 위에 한 층이 더 얹힌다:

**dotclaude 는 yoshinoid 의 flagship 이자 엔진이다.**

- **Flagship**: yoshinoid 가 실제로 어떻게 작동하는지 증명하는 live demo
- **Engine**: dotclaude-core 가 두 번째 yoshinoid 프로젝트의 공용 런타임이 됨

이 두 역할을 가능하게 하는 고유 동사: **"ship-through-evolving"**

yoshinoid 랩 전체가 dotclaude 가 만드는 evolve 루프로 살아있음을 유지한다.

## 4. yoshinoid 아이덴티티 레이어 — Hierarchy

```
yoshinoid (identity layer)
  ├── yoshinoid/.github               ← org README (I2)
  ├── yoshinoid/yoshinoid             ← 메타 레포 (manifesto, ideas/, shipped/)
  └── yoshinoid/<projects>
        ├── dotclaude (flagship, current)
        │     ├── dotclaude-core      ← Phase 1 에서 yoshinoid 공용화
        │     ├── dotclaude-cli
        │     ├── dotclaude-server
        │     └── dotclaude-rag
        └── project2 (future, Phase 2)
              └── depends on: dotclaude-core
```

### 4.1 yoshinoid 메타 레포 구조

`yoshinoid/yoshinoid` 레포 내부:

```
yoshinoid/
├── README.md                ← 브랜드 정체성 (태그라인, 철학, 4 키워드)
├── manifesto.md             ← 확장된 선언
├── ideas/                   ← I17: 독립 레포 대신 폴더로 시작
│   └── *.md
├── shipped/                 ← I18: live counter, project 완성 시 append
│   └── YYYY-MM-project.md
└── journal/                 ← I14: 주 1회 entry
    └── YYYY-Www.md
```

**ideas/ 승격 기준**: 10건 이상 축적 시 독립 레포 검토. 현재 폴더로 시작 (Premature abstraction 방지).

## 5. Fractal 포지셔닝 — 5층 Evolving

같은 "evolve" 동사가 계층마다 fractal 하게 반복된다:

```
사용자       → identity evolving
yoshinoid    → lab evolving
dotclaude    → setup evolving
dotclaude-core → kernel evolving
plug-ins     → domain evolving
```

이 구조가 yoshinoid 의 고유 포지셔닝을 만든다: 단순한 도구가 아니라 "yoshinoid 의 자기 진화 엔진".

## 6. Extract-After-Two-Uses 룰

`dotclaude-core` 의 yoshinoid 공용화는 premature abstraction 을 방지하기 위해 타이밍을 명시적으로 제어한다.

| Phase | dotclaude-core 상태 | 조건 |
|---|---|---|
| Phase 0 | dotclaude 전용 (Q3 spec 그대로) | — |
| Phase 1 | dotclaude 전용, yoshinoid 공용화 준비 | Phase 0 완료 |
| **Phase 2** | **yoshinoid 공용 런타임 승격** | **두 번째 yoshinoid 프로젝트 착수 시** |

**핵심 결정:**
- `dotclaude-core` **이름 유지** (rename 금지) — yoshinoid-core 로 변경 시 브랜드 정합성 약화 + 재작업 비용
- Stable core (도메인-universal): `classify_path`, `write_gateway`, `later_store`, `event_bus`
- Reference impl (override 가능): `evolve_kernel`

두 번째 프로젝트는 `from dotclaude_core.contracts import EvolvePlugin` 으로 그대로 임포트한다.

## 7. `dotclaude.self` scope 확장

Q3 spec §4.5 에서 `scope = "personal"` 필드가 이미 존재한다. Q4 에서 3단계로 확장한다.

| scope | instance | write_paths | Tier 제약 |
|---|---|---|---|
| `personal` | `~/.claude/**` | memory, docs, rules | Tier 0-2 |
| `project` | `<repo>/.claude/**` | project memory · spec | Tier 0-2 |
| `yoshinoid` | `yoshinoid/**` 레포들 | README mirror, ideas 승격, shipped 갱신 | **Tier 2 강제** |

**Tier 2 강제 근거**: 브랜드 수준 결정 = taste = AI 위임 한계선.
`user_ai_orchestration_role.md` 원칙: "taste 는 사람이 결정, 실행만 위임." yoshinoid README · manifesto 수정은 taste 영역이므로 항상 PR draft + 사용자 승인이 필요하다.

`plugin.toml` 에서의 선언 (확장):
```toml
[plugin]
scope = "yoshinoid"   # "personal" | "project" | "yoshinoid"
```

## 8. Evolution Timeline

Phase 간 시간 제약 없음 (12 앵커 자연 휴식 준수). 완료조건은 시간 기준이 아닌 증거 기준.

### Phase 0 — Foundation (NOW)

| 작업 | 비중 |
|---|---|
| dotclaude-core T1-T14 구현 | 85% |
| yoshinoid 메타 레포 + .github 레포 생성 | 15% |

세부 작업:
- (0.1) dotclaude-core T1-T14 구현 (Q3 spec §6 태스크 그대로)
- (0.2) yoshinoid 메타 레포 + .github 레포 생성
- (0.3) `yoshinoid/README.md` v1 작성
- (0.4) `yoshinoid/ideas/` 폴더 시작 (독립 레포 X)
- (0.5) dotclaude README 에 "A yoshinoid flagship" 링크 추가

**완료조건 (증거 중심):**
- [ ] Usage plug-in Tier 1 auto-commit 1회 이상 성공
- [ ] `yoshinoid/ideas/` 1건 이상
- [ ] `yoshinoid/README.md` v1 존재

### Phase 1 — Flagship Proof

- (1.1) `dotclaude.self scope=yoshinoid` 구현
- (1.2) 주 1회 auto-evolve commit 가동
- (1.3) 사내 발표 1회 (medium confidence)
- (1.4) 지인 1명 dotclaude user 시도

**완료조건:**
- [ ] 주 1회 yoshinoid auto-commit 4주 연속
- [ ] 지인 1명 usage signal → tribe store 유효 데이터
- [ ] 사내 발표 또는 블로그 1건

### Phase 2 — Second Project (extract-after-two-uses 발동)

- (2.1) `yoshinoid/ideas/` 에서 score ≥ 0.7 pick
- (2.2) 신규 레포 `yoshinoid/<project2>`
- (2.3) dotclaude-core 공통 extract + override 지점 확정
- (2.4) 지인 풀 1명 collaborator 초대 (옵션)

**완료조건:**
- [ ] project2 public release
- [ ] dotclaude-core 2 프로젝트 동시 가동

### Phase 3 — Multi-Project Lab

3+ 프로젝트, doctrine, publication rhythm — Phase 2 완료 시 재결정.

## 9. Sustainability 모델

### 비대칭 배분

주 25-40h 중:
- dotclaude: **~85%** (Q3 T1-T14 구현)
- yoshinoid: **~15%** (메타 레포 문서, ideas, 핵심 문구)

yoshinoid 운영은 "dotclaude 진행 중 자연 부산물"로 설계: `/spec` 으로 생성된 문서가 yoshinoid 메타 레포에 mirror 되는 구조가 되면 인지 부하 최소.

**주의**: 85/15 숫자 자체는 weak confidence. 원칙(비대칭)은 strong. 실제 수행 후 조정.

### 주간 ritual

| 상황 | 행동 |
|---|---|
| 본업 여유 | journal/ 직접 entry 작성 |
| 본업 바쁨 | `dotclaude.self scope=yoshinoid` auto-commit |

**"살아있음" 정의**: 주 1회 commit (사용자 + AI 합산). Dead brand 방지 최소 조건.

## 10. 회사 관계 3-Layer

```
Layer C1 — 공개 레이어      : yoshinoid org public 레포
Layer C2 — 사내 fork       : 회사 내부 GitHub fork + 사내 plug-in (기밀)
Layer C3 — 격리 원칙       : 사내 fork → 공개 역류 금지 (IP 보호)
```

**Re-implementation rule**: 사내 fork 의 plug-in 에서 공개 가치 있는 아이디어가 나올 경우, 기밀을 완전히 제거한 clean-room 재구현을 별도로 작성해 공개 레이어에 PR. 기존 사내 코드 직접 이식 금지.

사내 발표·블로그는 항상 공개 레이어(Layer C1) 기반.

**Confidence**: medium — IP 경계 원칙 수준. 사용자 회사 환경 관찰 데이터 부재로 구체 채널은 의도적 공백.

## 11. Governance

| 단계 | 형태 | 조건 |
|---|---|---|
| Phase 0 (solo) | 체크리스트: "yoshinoid 4 키워드 중 1개 이상 매핑" | 현재 |
| Phase 1+ (2+ 멤버) | 공식 governance 문서화 | Phase 1 완료 후 |

**키워드 충돌 해소 원칙**: 🎯 Personalized vs 🖼️ Showpiece 는 경쟁이 아니라 상호 보완. "극단까지 personalized 된 것이 가장 강력한 showpiece가 된다."

yoshinoid 철학 > dotclaude 개별 결정. 충돌 시 `user_identity_vision.md` 7축 + yoshinoid 4 키워드가 상위 규범.

## 12. Concrete Sample — 두 번째 yoshinoid 프로젝트 시나리오

Phase 2 시점, 사용자가 `yoshinoid/ideas/weekly-review-assistant.md` pick.

```bash
gh repo create yoshinoid/weekly-review-assistant --public
cd weekly-review-assistant
pip install dotclaude-core  # Phase 1 에서 yoshinoid 공용화된 버전
```

```toml
# plugin.toml
[plugin]
name = "weekly-review.core"
version = "0.1.0"
scope = "project"
entry = "weekly_review:WeeklyReviewPlugin"

[plugin.permissions]
read_paths = ["~/notes/**"]
write_paths = ["~/notes/reviews/**"]
```

```python
# weekly_review/plugin.py
from dotclaude_core.contracts import EvolvePlugin, Signal, WriteIntent, EvolvePlan

class WeeklyReviewPlugin:
    name = "weekly-review.core"
    version = "0.1.0"

    async def scan(self, ctx):
        return [Signal(source=self.name, kind="review.candidate", ...)]

    async def propose(self, signals, ctx):
        return EvolvePlan(plugin=self.name, signals=signals, intents=[
            WriteIntent(path=Path("~/notes/reviews/2027-W03.md"),
                        mode="create", content="...", reason="weekly review draft")
        ])

    async def apply(self, plan, ctx):
        return plan.intents

    async def explain(self, plan):
        return "이번 주 3개 노트에서 review draft 생성"
```

**Brand carrier 자동화 체인**:
1. project2 README 상단 자동 삽입: "A yoshinoid project · powered by dotclaude-core"
2. `dotclaude.self scope=yoshinoid` 감지 → `yoshinoid/shipped/2027-01-weekly-review.md` auto-commit (Tier 2 → PR draft)
3. `yoshinoid/README.md` projects 섹션 링크 자동 추가 제안

**멤버 합류 예시**: 지인 풀 프론트 중급 1명이 Stage A (dotclaude user) 6개월 후 Stage B (project collaborator) 진입.

## 13. 20 Key Decisions

| # | 결정 | 선택 | 근거 | Loop |
|---|---|---|---|---|
| D1 | Blueprint reuse | dotclaude-core 를 yoshinoid 공용 엔진 승격 | Showpiece-Driven, 🏰 Plug-in Nucleus | L1, L9, L19 |
| D2 | Extract 타이밍 | Phase 1 extract-after-two-uses | Premature abstraction 방지 | L6 |
| D3 | Rename | dotclaude-core 이름 유지 | 브랜드 정합성, 재작업 비용 | L19 |
| D4 | Brand carrier | 메타 레포(본체) + dotclaude README(live demo) | Showpiece 다중 채널 | L10, L18 |
| D5 | Meta-recursive scope | personal/project/yoshinoid 3 단계 | plugin.toml scope 필드, AI orchestration 렌즈 | L11 |
| D6 | scope=yoshinoid Tier | Tier 2 강제 | Taste = AI 위임 한계 | L11 |
| D7 | Second project 발굴 | ideas 폴더 + Scout + score 기반 | 12 앵커 Q10, Scout 설계 | L2, L5 |
| D8 | ideas 위치 | 메타 레포 폴더 (독립 레포 X, 10건 후 승격) | Premature abstraction 방지 | L17 |
| D9 | 멤버 pathway | Stage A (user) → Stage B (collaborator) | yoshinoid umbrella | L12 |
| D10 | Stage A 진입점 | dotclaude CLI + self-hosted 서버 opt-in | company_leverage 원칙 | L12 |
| D11 | 회사 관계 | 3-layer (공개/사내 fork/격리) | IP 원칙 | (앵커) |
| D12 | Phase 0 완료조건 | 증거 중심 (시간 중심 X) | 12 앵커 자연 휴식 | L13 |
| D13 | Time 배분 | 85 dotclaude / 15 yoshinoid | Q3 시간 예산 리스크 | (앵커) |
| D14 | 주간 ritual | journal/ 주 1회 (사용자 or AI) | 번아웃 방어 | L14, L20 |
| D15 | "살아있음" 정의 | 주 1회 commit (사용자+AI 합산) | Dead brand 방지 | L20 |
| D16 | Governance | 현재 체크리스트, Phase 1+ 공식화 | solo 상태 과도 회피 | L15 |
| D17 | 키워드 충돌 | Personalized ↔ Showpiece 상호 보완 | "극단 personalized = showpiece" | L15 |
| D18 | Yoshinoid 고유 동사 | "ship-through-evolving" | fractal 해석 | L3 |
| D19 | Fractal 포지셔닝 | 5층 evolving | L3 확장 | L8, L22 |
| D20 | Anthropic 경쟁 관계 | layer 관계 (distribution vs intelligence) | 경쟁 재해석 | L16 |

## 14. 12 Rejected Alternatives

| 대안 | 기각 이유 |
|---|---|
| dotclaude-core → yoshinoid-core rename | 브랜드 정합성 약화, 재작업 비용 |
| Phase 0 즉시 공용화 | Premature abstraction |
| yoshinoid-ideas 독립 레포 즉시 | 빈 레포 dead brand |
| 메타 레포 없이 dotclaude README 만 | yoshinoid 는 랩 정체성 — flagship 이 전체를 대표할 수 없음 |
| scope=yoshinoid 자동 쓰기 허용 | Taste = AI 위임 한계 |
| 시간 기반 phase deadline | 12 앵커 자연 휴식 위반 |
| 50/50 시간 배분 | Q3 T1-T14 규모 대비 비현실적 |
| 사내 plug-in 공개 역류 | IP 침해 |
| Anthropic 공식 정면 경쟁 선언 | layer 관계로 재포지셔닝 (distribution vs intelligence) |
| 공식 governance 즉시 (solo 에서) | solo 에 과도, 오버헤드만 추가 |
| 두 번째 프로젝트 이름 지금 결정 | blind guess 금지 (`feedback_identity_brainstorming.md`) |
| 주간 ritual 없음 | Dead brand 리스크 — 자동 commit 이 살아있음의 최소 보루 |

## 15. Convergence Evidence

| 항목 | 값 |
|---|---|
| Total loops | 24 / 25 |
| Insights | 20 (I1-I20) |
| Decisions | 20 (D1-D20) |
| Rejected alternatives | 12 |
| Convergence condition | consecutive_empty ≥ 3 at L24 |
| Angles covered | 15 (competitive, MVP, verb-centric, hierarchy, user-scenario, risk, constraint, positioning, blueprint-reuse, brand-carrier, meta-recursion, member-pathway, evolution-timeline, sustainability, governance) |

## 16. Intentionally Open

의도적으로 비워둔 항목. blind guess 금지 원칙에 따라 데이터 수집 후 결정.

| 항목 | 이유 | 위임처 |
|---|---|---|
| 두 번째 yoshinoid 프로젝트 구체 아이디어 | ideas 메커니즘으로 발굴해야 | `yoshinoid/ideas/` + Scout |
| 사내 공유 구체 채널 | 사용자 회사 환경 관찰 데이터 부재 | 사용자 직접 판단 |
| 도메인 구매 (yoshinoid.dev 등) | yoshinoid umbrella LATER | later.md |
| doctrine / publication rhythm 세부 | Phase 3 에서 실 데이터 기반 결정 | Phase 3 재결정 |

## 17. Deferred Items

`C:\Users\jeong\.claude\docs\later.md` 의 `## Deferred (self-evolver)` 섹션에 이미 append 됨.

**[Deferred] `later_items` schema scope 컬럼**
- 내용: `later_items` 테이블에 `scope TEXT` 컬럼 추가 (`personal / project / yoshinoid`)
- 트리거: Phase 1 → Phase 2 전환 시점
- 이유: 현재 yoshinoid scope 는 설계 단계, 실제 데이터 패턴 축적 후 schema 확장

## 18. Remaining Uncertainty

정직한 confidence 수준. 낙관적 추정 없음.

| 항목 | Confidence | 메모 |
|---|---|---|
| 회사 관계 3-layer 실현 가능성 | **medium** | 사용자 회사 환경 관찰 데이터 부재. 일반 IP 원칙 적용 수준. |
| Phase 1→2 전환 트리거 "score ≥ 0.7" 산출 | **medium** | Scout scoring 알고리즘 미정. ideas 메커니즘 가동 후 구체화. |
| 85/15 배분 수치 | **weak** | 원칙(비대칭)은 strong, 숫자 자체는 실제 수행 후 조정. |

## 19. Next Steps

**Phase 0 진입**: `dotclaude-core` T1-T14 구현 착수.

```
/plan dotclaude-core Phase 0 implementation
  → Q3 spec §6 태스크 참조 (T1-T14)
  → 우선순위: T1 (loader) → T2 (event_bus) → T3 (classify_path) → T4 (write_gateway) → T9 (later_store) → T14 (usage plug-in thin slice)
```

yoshinoid Phase 0 작업 (15% 비중):
1. `yoshinoid/.github` 레포 생성 + org README
2. `yoshinoid/yoshinoid` 메타 레포 생성
3. `yoshinoid/README.md` v1 (4 키워드 + 태그라인 + dotclaude flagship 링크)
4. `yoshinoid/ideas/` 폴더 첫 번째 entry

## 20. References

### 선행 Spec
- Q3: `2026-04-10-dotclaude-plugin-nucleus-architecture.md` (이 spec 의 전제, Q4 는 Q3 위에 얹히는 layer)

### 메모리 파일
- `user_dotclaude_q4_yoshinoid_flagship_intent_anchor.md` — Phase 1 앵커 (9개 질문, confidence 매핑)
- `project_yoshinoid_umbrella.md` — yoshinoid 상위 컨텍스트 (12 앵커, 4 키워드)
- `user_identity_vision.md` — 개발자 아이덴티티 7축 + 목표함수
- `user_ai_orchestration_role.md` — AI orchestration 렌즈 (taste 위임 한계)
- `user_dotclaude_keywords.md` — dotclaude 7 키워드 4계층 구조

### Brainstorming 세션 메타
- Source: self-evolver Q4 (SEB 자율 진행)
- Session date: 2026-04-10
- Total loops: 24 / 25
- 수렴 조건: consecutive_empty ≥ 3

## 21. 변경 이력

| 날짜 | 버전 | 변경 | 이유 |
|---|---|---|---|
| 2026-04-10 | 1 | 초안 생성 (self-evolver Q4 24-loop 수렴 결과) | Q3 spec 이후 yoshinoid 전략 영구 기록 |
| 2026-04-10 | 1.1 | §1, §5 문구 정리 | 사용자 요청 — 아키텍처 결정 변화 없음 |
