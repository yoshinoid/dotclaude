---
title: Infinite wait loop prevention (4-layer defense)
status: APPROVED
date: 2026-04-11
session_source: 2026-04-11-06
convergence_method: self-evolving-brainstorm (50 loops)
intent_anchor: ~/.claude/projects/C--Users-jeong-projects-yoshinoid/memory/user_infinite_wait_loop_prevention_intent_anchor.md
supersedes: (none — first iteration)
related_specs:
  - 2026-04-11-yoshinoid-phase-0-implementation-plan.md
  - 2026-04-11-knowledge-store-separation-and-rename-cascade.md
  - 2026-04-11-t6-plan-v3.1-approved.md
---

# Spec: Infinite wait loop prevention (4-layer defense)

## 1. Summary

4-layer defense against hook-induced infinite wait loops in Claude Code
sessions. Root fix on the triggering hook (L1), generalized detection rule
(L3+L4 merged), CLAUDE.md keystone hard_rule, plus a future upstream CLI
proposal (L2). Solves a class of failures rooted in coupling user-action-
required `{"decision": "block"}` to an async user input channel that may
stall.

## 2. Background

### 2.1 Incident timeline (2026-04-11-06 session)

- **Incident #1**: 80+ turn "대기" single-character loop during commit
  approval wait. User returned with frustration: "커밋해줘. 그리고 대기
  라고하면서 내가 중간에 요청한걸 무시하고 있어."
- **Incident #2** (same session, later): 10-turn "대기" loop after kv_store
  scope drift decision point
- **Incident #3** (same session, later still): 20-turn "동일. 결정 대기."
  short-repeated-response loop after batch 2+3 commit decision point
- Total: **~110 turns wasted across 3 loop events** in one session

### 2.2 Why memory rule v1 failed

A memory rule `feedback_infinite_wait_loop.md` was added after Incident #1
stating "동일 hook feedback 3회 연속 + 사용자 메시지 empty = escape hatch."
Incident #2 complied (agent escaped). Incident #3 regressed because the
memory rule only prohibited "대기" single-character repetition, not "동일.
결정 대기." multi-character short responses with the same semantic content.

**Meta lesson**: short repeated response ≠ single-character response. Both
are loop anti-patterns. Memory rule wording must be **semantic, not
lexical**.

### 2.3 Root cause (dual, coupled)

1. **Hook side**: `stop-commit-reminder.sh` returned `{"decision": "block",
   "reason": "..."}` to block Stop hook, intending to remind user to commit
2. **Channel side**: during the block, user input (e.g., `/commit`, "commit
   해줘") did not propagate from the OS input channel to the assistant's
   context. Only the hook stderr kept re-firing
3. **Agent side**: Claude interpreted "hook stderr repeating + no user
   message" as "user is still thinking," and responded with the shortest
   possible acknowledgment ("대기" or similar). This accelerated the loop
   instead of breaking it.

True root cause = **the coupling of user-action-required blockers to an
async channel that may stall**. Fix either side breaks the coupling.

## 3. Origin & Customization

- **Researched**: 2026-04-11 (SEB 50-loop convergence)
- **Landscape**: No directly applicable prior art.
  - LangGraph `interrupt_before` — uses checkpointer + resume token
    (structural), not memory/rule-based
  - AutoGen / CrewAI — max-turn / max-iteration caps, but not loop
    detection per se
  - VS Code "close with unsaved changes" — synchronous UI prompt, not async
    hook output
- **Key differentiators**:
  - Claude-Code-native: leverages existing rule/memory/hook system, no CLI
    change required for MVP (L1+L3+keystone)
  - Self-observation based: Claude reads its own outputs to detect the loop
    pattern, rather than relying on external state machine
  - Escape action strictly bounded to non-destructive set (stash/handoff/
    memory only); commit/push/drop remain manual-approval-required
- **Primary customizations**:
  - Anchored to CLAUDE.md `<hard_rules>` ecosystem (adds 7th hard rule)
  - Integrates with `feedback_no_approval.md` vs commit approval tension —
    resolved by the "autonomous = non-destructive only" boundary
  - Hook contract policy added to `agent-skill-creation.md` (existing rule)
    instead of creating a new `hook-writing.md` file (file sprawl avoided)

## 4. Decision (4-layer architecture)

### 4.1 Layer list

| Layer | 위치 | 목적 | 상태 this spec |
|---|---|---|---|
| **L0** | `session-start-context.sh` (existing) | 다음 세션 시작 시 미커밋 파일 수를 surface (기존 동작) | 재활용, 무변경 |
| **L1** | `stop-commit-reminder.sh` | Stop hook을 informational only로. `{"decision": "block"}` 제거, stderr print + exit 0 | **수정** (root fix) |
| **L2** | Upstream Claude Code CLI | CLI-level loop detection (동일 hook stderr N회 반복 + empty free-text → auto escape) | **Future work only** — 3-5 문장 제안서 (§6) |
| **L3+L4** | `~/.claude/rules/loop-escape.md` (신규) | Claude self-observation loop detection + escape hatch action + hook contract 연결 | **신규 rule file** |
| **Keystone** | `~/.claude/CLAUDE.md` `<hard_rules>` | `[HARD] 루프 탐지 의무` 신규 hard_rule | **편집** (keystone, essential) |

### 4.2 Trigger spec (embedded in `loop-escape.md`)

Loop confirmed only when **all 3 conditions AND** hold:

1. **Hook stderr repetition** — last N=3 turns' hook stderr has ≥80% lexical
   similarity. Numeric/timestamp/filecount variance counted as identical
2. **Empty user message** — last N=3 turns received zero free-text input
   from user. Slash commands, tool approvals, system-reminder responses are
   excluded (not "free text")
3. **Claude response flatness** — Claude's last N=3 responses have zero
   information delta: 95%+ identical content OR short (<50 chars) repeated
   response (covers "대기", "동일. 결정 대기.", "확인 중")

Single-condition matches are normal (verifier re-running is condition 1
only; user answering mid-stream breaks condition 2). Only the 3-way AND
fires the escape.

### 4.3 Escape hatch action sequence (embedded in `loop-escape.md`)

Strict order, step failure is best-effort (next step still attempted):

1. **Announce**: final message stating loop detected + action plan
2. **Preserve**: `git stash push -u -m "auto-stash: input channel stalled
   at <topic>"` (the `-u` flag is essential — untracked must be included)
3. **Write handoff**: `<cwd>/.claude/docs/handoff.md` with template
   including `stash_ref`, `topic`, `last_knowledge_entry`, `triggered_at`,
   restore command, last/next action, loop debug context
4. **Link**: update last knowledge entry's frontmatter to include
   `handoff_ref` (skip if knowledge store absent)
5. **Final report**: state + recovery method
6. **Silence**: Claude does not respond further until new session or
   explicit user input

### 4.4 Autonomous action boundary (Hard rule vs `feedback_no_approval`)

The loop-escape rule resolves the tension between:
- `feedback_no_approval.md` — "자율 진행 선호"
- CLAUDE.md hard rule — "NEVER commit without explicit user approval"

by defining:

| Category | Autonomous? | Why |
|---|---|---|
| `git stash push -u` | ✅ | Non-destructive preservation, reversible |
| Write handoff.md, memory, working/*.md, .claude/docs/*.md | ✅ | Non-destructive, within agent work area |
| `git commit` | ❌ | Externally visible, hard rule preserved |
| `git push` / pull | ❌ | Externally visible |
| `git stash drop` / pop | ❌ | Destroys preserved state |
| `rm`, `git clean`, `reset --hard` | ❌ | Destructive |
| Spec file creation | ❌ | Not escape-urgent, next session OK |

Rule of thumb: **non-destructive preservation = autonomous, external-
visible or destructive = approval required**. Hard rule "commit 승인 필수"
is preserved; `feedback_no_approval` stays valid within the preservation
scope.

### 4.5 Hook output contract (policy, in `agent-skill-creation.md`)

New hooks must follow:

- **Default pattern**: stderr print + exit 0 (informational)
- **`{"decision": "block"}` allowed only when**:
  1. Unblock condition is machine-verifiable (no user intervention)
  2. Bounded in time (hard timeout, not "forever")
  3. Block reason is data integrity or security (not user convenience)
- **Never use block for**:
  - User-action reminders (commit, review, check X)
  - Async I/O-dependent unblock conditions

This contract lives in `agent-skill-creation.md` (existing rule covering
hook writing), not a new `hook-writing.md` file — avoids file sprawl while
making the policy discoverable.

## 5. Implementation steps

| Step | Action | Files | Verification |
|---|---|---|---|
| A1 | CLAUDE.md `<hard_rules>` 추가 | `~/.claude/CLAUDE.md` + chezmoi source `dot_claude/CLAUDE.md` | grep `루프 탐지 의무` → present |
| A2 | Hook informational 전환 | `~/.claude/hooks/stop-commit-reminder.sh` + chezmoi source `dot_claude/hooks/executable_stop-commit-reminder.sh` | grep `decision.*block` → 0 hits |
| A3 | 신규 rule file | `~/.claude/rules/loop-escape.md` + chezmoi source `dot_claude/rules/loop-escape.md` | file exists in both |
| A4 | Hook contract section append | `~/.claude/rules/agent-skill-creation.md` + chezmoi source | grep `Hook output contract` → present |
| A5 | This spec file | `dotclaude-suite/dotclaude/.claude/docs/specs/2026-04-11-infinite-wait-loop-prevention.md` | file exists |
| A6 | later.md entry 상태 이동 | `~/.claude/knowledge/working/later.md` | Active → Done section with this spec link |
| A7 | memory file link 추가 | `feedback_infinite_wait_loop.md` | points to `loop-escape.md` rule |

**Sync policy** (exhaustive-sweep.md rule): A1~A4 는 live + chezmoi source
**양쪽 직접 편집** (not `chezmoi apply`). `chezmoi diff` 0 으로 확인.

**Commit grouping** (approval required, per hard rule):
- Commit 1: `feat(hooks,rules,memory): infinite wait loop prevention —
  4-layer defense (spec 2026-04-11)` bundling A1-A4 + A6-A7 (dotfiles repo)
- Commit 2: `docs(specs): add infinite wait loop prevention spec` for A5
  (dotclaude project repo)

## 6. Future work (L2 upstream proposal — 3-5 sentence blurb)

> **Proposal for Claude Code CLI runtime loop detection**
>
> Other agent frameworks (LangGraph, AutoGen, CrewAI) include explicit
> loop detection mechanisms. Claude Code currently depends on memory-file
> rules for this, which only activate if loaded into context. A native CLI
> feature that detects N=3 identical hook stderr messages combined with
> zero free-text user input, then auto-invokes a non-destructive escape
> (git stash + handoff write + session exit), would provide fail-safe
> protection independent of memory rule loading. This would make the
> `~/.claude/rules/loop-escape.md` rule a documentation reference rather
> than the only line of defense.

Submit this to the Claude Code issue tracker (anthropics/claude-code) when
ready. Not in scope for this spec's implementation.

## 7. Verification

### 7.1 Post-implementation sanity
- `grep -r "decision.*block" ~/.claude/hooks/` → 0 hits
- `chezmoi diff` → 0 (live matches source for all 4 edited files)
- `grep "루프 탐지 의무" ~/.claude/CLAUDE.md` → 1 hit
- `ls ~/.claude/rules/loop-escape.md` → exists
- `grep "Hook output contract" ~/.claude/rules/agent-skill-creation.md` → 1 hit

### 7.2 Trigger reproduction test (manual, next session)
- Mock a hook returning `{"decision": "block"}` 3 turns in a row
- Expected: agent self-observes loop after turn 3, executes escape hatch
  (stash + handoff write), session exits cleanly
- Recovery: next session `git stash pop` + `/handoff --resume` restores
  state

### 7.3 Regression monitoring
- Add `~/.claude/knowledge/` session-close entries (once T6-13 is
  implemented) should flag any new 10+ turn short-response repetition as a
  loop regression indicator

## 8. Alternatives considered (and rejected)

Full list preserved from SEB Phase 3 report for audit:

| # | 대안 | 기각 이유 |
|---|---|---|
| 1 | L1 only (hook fix만) | 일반화 부재 — 미래 다른 hook 동일 실수 시 재발. Intent "중요도 높음" 위반 |
| 2 | L3 only (rule 만, hook 유지) | Root 미제거. Brittle |
| 3 | Hard rule softening | `feedback_no_approval` vs commit 원칙 충돌 재활성화 |
| 4 | `settings.json` 수정으로 hook 비활성화 | CLAUDE.md hard rule #9 (settings.json touch 금지) 위반 |
| 5 | Upstream CLI runtime 탐지 먼저 | 이번 session scope 밖, L2 로 defer |
| 6 | 탐지 조건 단순화 (hook stderr만, user msg 조건 없이) | False positive (verifier 정상 반복 오탐) |
| 7 | Escape hatch 에 `git commit` 자동 포함 | Q3 anchor 위반, hard rule 위반 |
| 8 | `hook-stall-recovery.md` 이름 | 너무 좁은 naming. Loop escape 는 일반화 가능 |
| 9 | Rule only, CLAUDE.md hard_rule 생략 | Keystone 부재 → empty user msg 시 topic 기반 rule load 불가 → rule dormant when most needed |
| 10 | 신규 `hook-writing.md` 파일 | File sprawl. `agent-skill-creation.md` 이미 커버 |
| 11 | Escape hatch announce 후 3초 대기 | 전제가 input stall → 3초 대기 무의미 |

## 9. Open questions (resolved or deferred)

- **Resolved**: 재발 탐지 threshold → N=3 with 3 AND conditions
- **Resolved**: Rule file location → `~/.claude/rules/loop-escape.md` (not a new dir)
- **Resolved**: Hook contract location → `agent-skill-creation.md` section append
- **Resolved**: `feedback_no_approval` vs hard rule → non-destructive/destructive split
- **Deferred to L2 future work**: CLI runtime auto-detection
- **Deferred (optional enhancement)**: session-start OS notify for unstaged
  files
- **Deferred (optional enhancement)**: `stash@{0}` auto-surface in
  session-start-context.sh on new session
- **Deferred**: Audit other hooks in `~/.claude/hooks/` for `decision.*block`
  usage (periodic grep recommended, not automated)

## 10. Change history

| Date | Version | Change | Reason |
|---|---|---|---|
| 2026-04-11 | 1 | 초안 생성 (SEB 50-loop 수렴 결과) | 2026-04-11-06 세션 2회 재발 post-mortem |
