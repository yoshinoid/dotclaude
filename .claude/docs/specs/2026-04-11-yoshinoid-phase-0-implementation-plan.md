---
title: yoshinoid Phase 0 Implementation Plan (planner v2 + critic Round 2 CONDITIONAL APPROVAL)
date: 2026-04-11
status: approved (CONDITIONAL — 4 trivial fixes inlined; ready for implementation entry)
version: 1
id: 2026-04-11-yoshinoid-phase-0-implementation-plan
owner: jeonghwan-hwang (yoshinoid)
source: planner Round 1 + critic Round 1 (NEEDS REVISION) + planner Round 2 + critic Round 2 (CONDITIONAL APPROVAL, 4 inline fixes applied)
related_specs:
  - 2026-04-10-yoshinoid-meta-agent-phase-0.md (v2.1 — §7.2 Track 1 Done criteria 추가됨)
  - 2026-04-10-dotclaude-plugin-nucleus-architecture.md (v1.1 — Extension rename note 추가됨)
  - 2026-04-10-dotclaude-yoshinoid-flagship-alignment.md (v1.2)
related_rules:
  - ~/.claude/rules/agent-skill-creation.md
related_docs:
  - ~/.claude/docs/later.md (★★★ Phase 0 실행 계획)
  - ~/.claude/projects/c--Users-jeong-projects-yoshinoid/memory/project_meta_agent_family.md
---

# Spec: yoshinoid Phase 0 Implementation Plan

이 spec 은 Phase 0 spec v2.1 의 Done criteria (Track 1 C7-C11 + Track 2 C1-C6) 을 달성하기 위한 **구현 계획서** 다. plan ↔ spec 분리: Phase 0 spec 은 "무엇을 만드는가", 본 spec 은 "어떻게/순서/검증". planner 2 round + critic 2 round 를 거쳐 CONDITIONAL APPROVAL 로 진입 ready 상태.

---

## 1. Naming Decision (P0-1 해결)

dotclaude-core 의 module 시스템은 **`Extension`** 으로 명명한다.

- **이유 1**: 기존 `c:/Users/jeong/projects/yoshinoid/dotclaude-suite/dotclaude/src/dotclaude/parser/parsers/plugins.py` 의 `PluginsStatus` (Claude Code marketplace plug-in 파싱) 와 어휘 격리
- **이유 2**: Q3 spec 의 `EvolvePlugin` Protocol 은 spec 자체 고유 식별자이므로 **타입 이름만 `EvolveExtension` 으로 rename** (Q3 spec §15 v1.1 note 에 alias 기록 완료)
- **이유 3**: "extension" 은 파이썬 생태계 (`pytest`, `mkdocs`) 에서 load/registry 의미로 굳은 단어
- **이유 4**: `plugin.toml` → **`extension.toml`**, `loader.py` → `extension_loader.py`, `registry.py` → `extension_registry.py` 일관 변경

**잔존 검증 게이트** (V 단계, critic P0-b + 2026-04-11 T1-T3 후기 보강):
```bash
rg -w 'plugin|Plugin' dotclaude-core/ dotclaude-usage/ \
  --glob '!**/parsers/plugins.py' \
  --glob '!**/q3-*.md' \
  --glob '!**/extension.toml' \
  --glob '!**/.venv/**' \
  --glob '!**/.pytest_cache/**' \
  --glob '!**/.git/**' \
  --glob '!**/build/**' \
  --glob '!**/dist/**' \
  --glob '!**/*.egg-info/**' \
| rg -v '(# allow-plugin-word|<!-- allow-plugin-word -->)' \
| wc -l
# 결과 == 0 이어야 함
```

**Allowlist 규칙**:

1. **File-glob allowlist** (위 `--glob '!...'` 목록):
   - `parsers/plugins.py` — 기존 dotclaude CLI namespace (Claude Code marketplace 파서), 불변
   - `q3-*.md` — Q3 spec 본문 (rename 이전 원문)
   - `extension.toml` — 확장 manifest 파일 (내부 `[extension]` 섹션 선언은 OK)
   - `.venv/`, `.pytest_cache/`, `.git/`, `build/`, `dist/`, `*.egg-info/` — build/runtime 산출물 (third-party 포함)

2. **Line-level allowlist** — 두 형식 모두 허용:
   - `# allow-plugin-word` — Python/TOML/YAML/shell 주석 형식
   - `<!-- allow-plugin-word -->` — Markdown/HTML 주석 형식

3. **Docstring 주의**: Python docstring 내부의 "plugin" 단어는 line-level 마커로 exempt 불가 (주석이 아니므로). 반드시 **rewording** 으로 제거할 것. 역사적 spec 이름을 참조해야 할 경우 "see plan spec §1" 같은 간접 참조 사용.

fail 시 **수동 fix** (자동 rollback 금지 — 위험).

---

## 2. Q3 spec T# ↔ 본 plan T# Mapping

| Q3 T# | 정의 | plan T# | 주요 파일 |
|---|---|---|---|
| T1 | dotclaude-core 레포 init | T1 | `dotclaude-core/{pyproject.toml, dotclaude_core/__init__.py, .gitignore, README.md}` |
| T2 | contracts.py (Signal/WriteIntent/EvolvePlan/EvolveResult/`EvolveExtension` Protocol) | T2 | `dotclaude_core/contracts.py` |
| T3 | classify_path.py (Tier 0/1/2/3) **+ Windows path normalization** | T3 | `dotclaude_core/classify_path.py` |
| T4 | write_gateway.py | T4 | `dotclaude_core/write_gateway.py` |
| T5 | git_ops.py | T5 | `dotclaude_core/git_ops.py` |
| T6 | later_store.py (sqlite + event publish) | T6 | `dotclaude_core/later_store.py` |
| T7 | event_bus.py | T7 | `dotclaude_core/event_bus.py` |
| T8 | extension_loader + registry (extension.toml parse) | T8 | `dotclaude_core/{extension_loader.py, extension_registry.py}` |
| T9 | evolve_kernel.py | T9 | `dotclaude_core/evolve_kernel.py` |
| T10 | safety/ 모듈 | **T10a + T10b** (split, P0-3) | `dotclaude_core/safety/{permissions.py, file_lock.py, sandbox.py}` |
| T11 | dotclaude-usage thin slice | T11 | `dotclaude-usage/**` |
| T12 | 단위 테스트 | T12 | `dotclaude-core/tests/unit/**` |
| T13 | E2E (Usage 아침 루프) | T13 | `dotclaude-core/tests/e2e/test_usage_slice.py` |
| T14 | dotclaude CLI 점진 이관 (extension wrapping) | T14 | `dotclaude/src/dotclaude/extensions/` (신규) |

---

## 3. 영향받는 파일 (4 카테고리)

### A. 신규 생성 (Track 1 — dotclaude-core, 33 파일)

- **packaging**: `c:/Users/jeong/projects/yoshinoid/dotclaude-suite/dotclaude-core/{pyproject.toml, README.md, .gitignore, ruff.toml}`
- **core src** (15): `dotclaude_core/{__init__, contracts, config, classify_path, write_gateway, git_ops, later_store, event_bus, extension_loader, extension_registry, evolve_kernel, kv_store, scheduler}.py`
- **safety** (4): `dotclaude_core/safety/{__init__, permissions, file_lock, sandbox}.py`
- **tests unit** (8): `tests/unit/{conftest, test_contracts, test_classify_path, test_write_gateway, test_later_store, test_permissions, test_extension_loader, test_git_ops, test_event_bus}.py`
- **tests e2e** (2): `tests/e2e/{conftest, test_usage_slice}.py`

### A'. 신규 생성 (Track 1 — dotclaude-usage, 7 파일)

- `c:/Users/jeong/projects/yoshinoid/dotclaude-suite/dotclaude-usage/{pyproject.toml, extension.toml, README.md}`
- `dotclaude_usage/{__init__.py, extension.py, scanners/hook_failure_scanner.py, proposers/memory_update_proposer.py, templates/usage_report.md.j2}`
- `tests/test_usage_extension.py`

### A''. 신규 생성 (Track 2 — 글로벌 yoshinoid kernel, 5 파일)

- `c:/Users/jeong/.claude/agents/yoshinoid.md`
- `c:/Users/jeong/.claude/memory/yoshinoid_state.md`
- `c:/Users/jeong/.claude/memory/yoshinoid_patterns.md`
- `c:/Users/jeong/.claude/memory/yoshinoid_corrections.md`
- `c:/Users/jeong/.claude/hooks/yoshinoid-writer.sh`

### B. 수정 (3 파일, spec only)

- `c:/Users/jeong/projects/yoshinoid/dotclaude-suite/dotclaude/.claude/docs/specs/2026-04-10-yoshinoid-meta-agent-phase-0.md` ✅ TS-1 적용 완료 (§7.2 Track 1 criteria + §15 v2.1)
- `c:/Users/jeong/projects/yoshinoid/dotclaude-suite/dotclaude/.claude/docs/specs/2026-04-10-dotclaude-plugin-nucleus-architecture.md` ✅ TS-2 적용 완료 (§16 v1.1 Extension rename note)
- (선택, T14 후) `c:/Users/jeong/projects/yoshinoid/dotclaude-suite/dotclaude/src/dotclaude/__init__.py` — 신규 `dotclaude.extensions` namespace export

### C. 참조만 (read-only)

- Phase 0 spec v2.1
- Q3 spec v1.1
- Q4 spec v1.2
- `~/.claude/docs/later.md` yoshinoid 섹션
- `~/.claude/docs/research.md` yoshinoid landscape entry
- 메모리 파일들

### D. 건드리면 안 됨 (HARD 제약)

- `c:/Users/jeong/.claude/memory/secretary_*.md`, `career_*.md`, `ideamgr_*.md` — **생성 금지** (HARD #5 lens namespace)
- `c:/Users/jeong/.claude/settings.json` — chezmoi 회피 (HARD #9)
- `**/.env*`, `*.pem`, `*_secret*`, `*_key*` (HARD #8)
- `c:/Users/jeong/projects/yoshinoid/dotclaude-suite/dotclaude/src/dotclaude/parser/parsers/plugins.py` — 기존 namespace 보호 (P0-1)
- 기존 `dotclaude/src/dotclaude/**` Phase 0 = wrapping 없음 (T14 만 새 sub-module 추가)

---

## 4. Task Table

| # | Task | 파일 | Depends | DoD |
|---|---|---|---|---|
| **TT2-0** | §16 family snapshot sha256 기록 | `~/.claude/memory/yoshinoid_state.md` (TT2-3 후) | TT2-3 | sha256 of Phase 0 spec §16 block 기록. **검증 주체**: verifier hook (`~/.claude/hooks/yoshinoid-verifier.sh`, 신규), 매 세션 시작 시 자동 비교, mismatch 시 즉시 세션 중단 + handoff.md 알림 (critic P1-a) |
| **TS-1** | Phase 0 spec §7.2 C7a/C7b/C8/C9/C10/C11 + §15 v2.1 | Phase 0 spec | — | ✅ **완료** (이 세션 적용) |
| **TS-2** | Q3 spec §15 v1.1 Extension rename note | Q3 spec | — | ✅ **완료** (이 세션 적용). **critic 회귀 예외**: TS-1/TS-2 는 patch-level spec update 라 critic 생략, code-reviewer 만 호출 (P1-c) |
| **T1** | dotclaude-core repo init | `dotclaude-core/{pyproject.toml, dotclaude_core/__init__.py, .gitignore, README.md, ruff.toml}` | — | `uv sync && python -c "import dotclaude_core"` green. python 3.11+ pinned |
| **T2** | contracts.py — Signal/WriteIntent/EvolvePlan/EvolveResult/`EvolveExtension` Protocol | `dotclaude_core/contracts.py` | T1 | pydantic v2 BaseModel + `EvolveExtension(Protocol)` runtime_checkable. mypy strict. 단위 테스트 15+ |
| **T3** | classify_path.py + Windows normalization | `dotclaude_core/classify_path.py`, `config.py` | T2 | (P0-2) `pathlib.PurePosixPath(str(p).replace('\\\\', '/'))` 강제. Tier 3 patterns: `.env*, *.pem, *_secret*, *_key*, .git/config`. **Windows 경로 케이스 8+** (`c:\\Users\\x\\.env`, `C:/x/secret.key`, mixed backslash, UNC `\\\\server\\share\\.env`, symlink → `.env`, etc) → POSIX 결과와 동일성 assertion |
| **T10a** | safety/permissions.py — manifest write_paths matcher | `dotclaude_core/safety/permissions.py` | T2 | (P0-3 split, T4 의 before) glob expansion. 단위 테스트 분해: Tier1 ≥4, Tier2 ≥4, Tier3 ≥6, negative ≥4 (P2-a, 총 18+) |
| **T4** | write_gateway.py | `dotclaude_core/write_gateway.py` | T3, T10a | Tier 0 immediate, Tier 1 staged, Tier 2 later_store pending, **Tier 3 reject**. 커버리지 ≥ 95% |
| **T5** | git_ops.py | `dotclaude_core/git_ops.py` | T1 | `branch, commit, diff, revert, current_branch, dirty_check`. subprocess wrapper. tmp git repo fixture 검증 |
| **T7** | event_bus.py | `dotclaude_core/event_bus.py` | T1 | asyncio.Queue 기반. publish/subscribe. fan-out 테스트. **redis adapter Protocol stub only** (Phase 0.5 본구현) |
| **T6** | later_store.py | `dotclaude_core/later_store.py`, `kv_store.py` | T1, T7 | sqlite schema (Q3 §4.7). status 전환 시 `event_bus.publish("later.status_changed")`. WAL mode (Windows 시 `journal_mode=DELETE` fallback). **단일 파일 `dotclaude.sqlite`** (kv 와 share, 분리 테이블) |
| **T8** | extension_loader.py + extension_registry.py | `dotclaude_core/{extension_loader.py, extension_registry.py}` | T2 | `tomllib` parse → schema validate → entry import → instantiate. duplicate name reject |
| **T9** | evolve_kernel.py | `dotclaude_core/evolve_kernel.py` | T4, T6, T7, T8 | scan → propose → dry_merge → apply. 충돌 시 둘 다 Tier 2 escalate |
| **T10b** | safety/file_lock.py + sandbox.py | `dotclaude_core/safety/{file_lock.py, sandbox.py}` | T4 | file_lock: mtime + git-dirty. sandbox: asyncio timeout + posix `resource` (windows = pragma). `# pragma: no cover` 허용 (P1-3) |
| **T11** | dotclaude-usage thin slice | `dotclaude-usage/**` | T2, T8 | seed Signal 3 → 2 WriteIntent (Tier 0 reports + Tier 1 memory). Q3 §4.9 시나리오 재현 |
| **T12** | 단위 테스트 (전체 모듈) | `dotclaude-core/tests/unit/**` | T2~T10b | 핵심 3 (contracts/classify_path/write_gateway) ≥ 95%, 전체 ≥ 75% (P1-3) |
| **T13** | E2E Usage 아침 루프 (tmp git repo) | `tests/e2e/test_usage_slice.py, conftest.py` | T11, T12 | `tmp_git_home` fixture + `YOSHINOID_HOME` env override (P2-2). assertion: branch + commit + reports/ + memory patch. **C7a 증명** |
| ~~T14~~ | ~~dotclaude CLI extension wrapping shim~~ | — | — | **DEFERRED to Phase 1** (Q-i resolved 2026-04-11). Phase 0 시간 예산 보호. 기존 `dotclaude/src/dotclaude/` 는 Phase 0 wrapping 대상 아님 |
| **TT2-1** | yoshinoid-writer.sh + Python resolver | `~/.claude/hooks/yoshinoid-writer.sh` | — | (P0-4) `CANONICAL=$(python -c "import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve(strict=True))" "$1")`. 단위 테스트: traversal 거부 (`../../etc/passwd`, symlink → `/etc/shadow`, agent 파일) |
| **TT2-2** | `agents/yoshinoid.md` | `~/.claude/agents/yoshinoid.md` | TT2-1 | frontmatter `tools: [Read, Grep, Glob]`. 9 섹션 (Phase 0 spec §6.3) + Origin 섹션 (research.md 앵커) |
| **TT2-3** | memory 3 파일 seed | `~/.claude/memory/yoshinoid_{state,patterns,corrections}.md` | TT2-2 | spec §6.4 schema. seed 5 patterns. suggestions_total=0 |
| **TT2-4** | `@yoshinoid` explicit 호출 3회 + correction 1건 | session log + memory | TT2-3 | C1 ≥ 3, C2 ≥ 5, C3 ≥ 1. **수동** (자동화 금지, A5) |
| **TT2-5** | dotclaude-core README v1 | `dotclaude-core/README.md` | T13, TT2-4 | C8: Usage extension demo + yoshinoid kernel 연결 섹션 |
| **V** | 최종 verifier — spec §14 + §7.2 C1-C11 | all | T13, T14, TT2-5 | 7.4 자동 체크 명령 전부 green |

### Critical path (선형, 순환 0)

```
TS-1 ✅ → TS-2 ✅ → T1 → T2 → T3 → T10a → T4 → T9 → T13 → V
                       ↘ T5/T7/T8 (parallel)
                          T6 (depends T7)
                          T10b (depends T4)
                          T11 → T12 (parallel with T13)
                          (T14 Phase 1 defer)

  TT2-1 → TT2-2 → TT2-3 → TT2-0 → TT2-4 → TT2-5 → V
  (Track 2, Track 1 와 거의 독립)
```

핵심 7 hop: **T1 → T2 → T10a → T4 → T9 → T13 → V**

---

## 5. Risks (11)

| # | Risk | P | 완화 |
|---|---|---|---|
| R-1 | 32+ 파일 단일 세션 미달성 | H | TT2-* 병렬 + 핵심 95% / 전체 75% (P1-3) |
| R-2 | Windows path Tier 3 우회 | H | T3 DoD Windows 8 케이스 강제 (P0-2) |
| R-3 | writer hook traversal | H | TT2-1 Python resolver (P0-4) |
| R-4 | file_lock OS race | M | pragma no cover 허용 |
| R-5 | sqlite WAL on Windows | M | `journal_mode=DELETE` fallback in T6 |
| R-6 | extension.toml schema drift | M | pydantic validator + T12 reject 테스트 |
| R-7 | T14 namespace 충돌 (`parsers/plugins.py`) | M | Extension naming + 신규 `dotclaude.extensions` path. 기존 plugins.py 불변 (P0-1) |
| R-8 | mypy strict 시간 초과 | L | core only strict, tests basic |
| R-9 | "Plugin" 단어 잔존 | M | rg gate + allowlist (P0-b 적용) |
| R-10 | §16 family snapshot drift 무감지 | M | TT2-0 sha256 + verifier hook 자동 비교 (P1-a) |
| R-11 | 2단 C7a/C7b drift | M | TS-1 적용됨 + C7b 7-day trigger 명시 (P0-a) |

---

## 6. Open Questions (잔존)

| # | Q | 결정 | Status |
|---|---|---|---|
| Q-a | event_bus 구현체 | asyncio.Queue 내장 + redis adapter Protocol stub | resolved |
| Q-b | later.md 경로 | `~/.claude/docs/later.md` 고정 | resolved |
| Q-c | kv_store + later_store sqlite 분리 | 단일 파일 `dotclaude.sqlite` | resolved |
| Q-d | Tier 1 auto-commit production target | Phase 0 = tmp E2E (C7a). production = Phase 0.5 logbook (C7b, 7-day trigger) | resolved (autonomous) |
| Q-e | dotclaude-usage 별 레포 vs sub-folder | 별 디렉토리 (`dotclaude-usage/`) | resolved |
| Q-f | coverage 목표 | 핵심 95% / 전체 75% | resolved (P1-3) |
| Q-g | writer hook validator bash vs python | Python resolver inline (P0-4) | resolved |
| Q-h | extension.toml vs dotclaude.toml vs `[tool.dotclaude.extension]` | **`extension.toml`** 유지 — Napari/Home Assistant 식 별도 manifest. entry_points 는 import path 만 노출로 부족. local-first directory discovery 모델 (PyPI 배포 전제 아님). research.md entry `2026-04-11 python-extension-manifest-conventions` | resolved (2026-04-11) |
| Q-i | T14 시간 예산 — Phase 0 에 포함 vs Phase 1 으로 defer | **Phase 1 defer** (default 적용) — Phase 0 시간 예산 보호. 기존 `dotclaude/src/dotclaude/` Phase 0 에서 건드리지 않음. dotclaude-core + dotclaude-usage thin slice + Track 2 kernel 만으로 Done criteria 달성. T14 는 Phase 1 엔트리로 이동 | resolved (2026-04-11, autonomous default) |

---

## 7. Verification Strategy

### 7.1 단위 (T12)
- 핵심 3 (contracts/classify_path/write_gateway) ≥ 95%
- 전체 dotclaude_core ≥ 75%
- safety/sandbox + safety/file_lock 일부 `# pragma: no cover` 허용
- T3 Windows 8 케이스 + traversal 3 케이스
- T10a 분해: Tier1 ≥4, Tier2 ≥4, Tier3 ≥6, negative ≥4

### 7.2 통합
- extension.toml parse → EvolveExtension instantiate
- evolve_kernel end-to-end with in-mem event_bus

### 7.3 E2E
- **C7a (T13)**: tmp git repo + `YOSHINOID_HOME=$TMP` + scan/propose/apply/commit assertion
- **C7b (deferred Phase 0.5)**: production target 1회 (logbook)
- **C1/C2/C3 (TT2-4)**: `@yoshinoid` 3회 + correction 1건 (수동)

### 7.4 Done 자동 체크 (V)

```bash
# coverage
pytest dotclaude-core/tests/ -v --cov=dotclaude_core --cov-fail-under=75
pytest dotclaude-core/tests/unit/test_{contracts,classify_path,write_gateway}.py --cov-fail-under=95

# C11 naming
rg -w 'plugin|Plugin' dotclaude-core/ dotclaude-usage/ \
  --glob '!**/parsers/plugins.py' \
  --glob '!**/extension.toml' \
| rg -v '# allow-plugin-word' | wc -l  # == 0

# C10 family snapshot
sha256sum_phase0_section_16=$(awk '/^## 16\./,/^## [0-9]+\./' Phase0_spec | sha256sum)
recorded=$(grep "family_snapshot:" ~/.claude/memory/yoshinoid_state.md | awk '{print $2}')
[ "$sha256sum_phase0_section_16" == "$recorded" ] || exit 1

# C1/C2 agent counters
grep -c 'suggestions_total: [3-9]' ~/.claude/memory/yoshinoid_state.md
grep -c 'corrections_count: [1-9]' ~/.claude/memory/yoshinoid_state.md

# C7b deferred trigger
[ -f handoff.md ] && grep -q "C7b deferred" handoff.md  # 7-day timer 등록 확인
```

---

## 8. 첫 5 액션 (revised — P0/P1 무력화 우선)

1. **Q-h 5분 research** (P1-b) — `extension.toml` vs `pyproject.toml [tool.dotclaude.extension]` 표준성 grep. 결과 무관 결정 기록 후 진입
2. **Q-i 사용자 결정** (P1-d) — T14 (CLI extension wrapping) 을 Phase 0 에 포함할지 Phase 1 으로 defer 할지. **default = Phase 1 defer** (Phase 0 시간 예산 보호)
3. **T1 + T2** — dotclaude-core init + contracts.py (`EvolveExtension` Protocol 명명 확정)
4. **T3 (test-first)** — classify_path Windows 8 케이스 단위 테스트 먼저 → 구현 → green
5. **TT2-1 병렬 시작** — yoshinoid-writer.sh + Python resolver + traversal 거부 테스트

---

## 9. Critic 적용 이력

- **Round 1 (planner v1)**: 4 P0 + 3 P1 (NEEDS REVISION)
- **Round 2 (planner v2)**: P0-a (C7b 7-day trigger) + P0-b (rg allowlist) + P1-a (verifier hook) + P1-c (TS-1/TS-2 critic 회귀 예외) → CONDITIONAL APPROVAL
- **본 spec**: 4 inline fix 모두 반영 완료
- **Q-h resolved (2026-04-11)**: 5분 research 후 `extension.toml` 유지. research.md entry `2026-04-11 python-extension-manifest-conventions`
- **Q-i resolved (2026-04-11, autonomous default)**: T14 Phase 1 defer. task table strikethrough

---

## 10. 변경 이력

| 날짜 | 버전 | 변경 | 이유 |
|---|---|---|---|
| 2026-04-11 | 1 | 초안 생성 (planner v2 + critic Round 2 CONDITIONAL APPROVAL, 4 fix inline) | Phase 0 implementation entry 전 plan 영구 기록 |
| 2026-04-11 | 1.1 | Q-h resolved (extension.toml 유지, research.md link) + Q-i resolved (T14 Phase 1 defer, task/critical path strikethrough) | 첫 액션 전 미결 질문 해소 → T1 진입 ready |
| 2026-04-11 | 1.2 | §1 ripgrep gate allowlist 확장 (.venv/.pytest_cache/.git/build/dist/*.egg-info) + markdown `<!-- allow-plugin-word -->` 마커 허용 + docstring rewording 규칙 명시 | T1-T3 구현 후 발견: build/runtime 산출물이 false positive 유발, docstring 내부 단어는 line-level marker 로 exempt 불가 |
