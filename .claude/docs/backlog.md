---
phase_order: [spark, queued, designed, active, done, archived]
migrated_from:
  source_root: ~/projects/yoshinoid/dotclaude-suite/dotclaude
  later: .claude/docs/later.md
  ideas: .claude/docs/ideas.md
migrated_at: 2026-04-17
generator: ab71b214b897
---

# Backlog

## Phase: spark

### Knowledge Collection Pipeline (적재 파이프라인)

<!-- phase: spark | source_file: .claude/docs/ideas.md | source_line: 6 -->

- 날짜: 2026-04-09
- 배경: dotclaude의 방향이 "Claude Code 운영 플랫폼"으로 확정. CLI가 설정 파일 수집기(collector) 역할을 해야 함
- 개요: `dotclaude sync` 시 기존 사용 데이터 스냅샷 외에 rules/agents/skills/commands/.md 파일을 파싱하여 서버에 업로드. 메타데이터(파일 종류, 대상 스택, 적용 범위) 자동 추출
- 열린 질문: 메타데이터를 frontmatter에서 읽을지 LLM으로 추출할지 (frontmatter 우선, fallback으로 규칙 기반 추출 유력)
- 상태: Phase 1 설계 필요

### Standard Frontmatter Formatter

<!-- phase: spark | source_file: .claude/docs/ideas.md | source_line: 13 -->

- 날짜: 2026-04-09
- 배경: RAG 적재 품질을 위해 모든 .md 설정 파일에 표준 frontmatter가 필요. 현재 대부분 frontmatter 없음
- 개요: `dotclaude format` 명령으로 ~/.claude/ 내 모든 rules/agents/skills/commands에 표준 frontmatter 자동 적용. 기존 내용 보존하면서 메타데이터만 추가
- 열린 질문: frontmatter 스펙은 dotclaude-types에서 정의. 이미 frontmatter가 있는 파일의 머지 전략
- 상태: Phase 1 설계 필요

### Plugin System for Custom Parsers

<!-- phase: spark | source_file: .claude/docs/ideas.md | source_line: 33 -->

- 날짜: 2026-04-09
- 배경: 현재 parser/parsers/에 하드코딩된 파서만 존재. 사용자마다 분석하고 싶은 데이터가 다를 수 있음
- 개요: 외부 파서 플러그인을 등록하고 로드하는 시스템
- 상태: 탐색 중

### Interactive Dashboard Mode

<!-- phase: spark | source_file: .claude/docs/ideas.md | source_line: 39 -->

- 날짜: 2026-04-09
- 배경: 현재 Rich 대시보드는 정적 출력. 실시간으로 필터링하거나 드릴다운하고 싶을 때 불편
- 개요: Textual 기반 TUI로 인터랙티브 대시보드 구현
- 상태: 탐색 중

### Cost Alert Threshold

<!-- phase: spark | source_file: .claude/docs/ideas.md | source_line: 45 -->

- 날짜: 2026-04-09
- 배경: 토큰 비용이 예상보다 급증할 때 알림이 없음
- 개요: 일/주/월 비용 임계값을 설정하고, analyze 실행 시 초과 여부를 경고
- 상태: 탐색 중

### Knowledge Collector Agent (주기적 프로젝트 프로파일링)

<!-- phase: spark | source_file: .claude/docs/ideas.md | source_line: 51 -->

- 날짜: 2026-04-09
- 출처: later.md
- 배경: 프로젝트마다 tech stack, 프레임워크, 규모, 컨벤션이 다름. 이 정보를 자동 수집해야 RAG 추천 품질이 올라감
- 개요: 주기적으로 프로젝트 컨텍스트 데이터를 수집하여 `.claude/knowledge/project-profile.json` 저장. claude-config이 참조하여 더 나은 추천 제공
- 관계: Knowledge Collection Pipeline의 입력 데이터 생성기
- 상태: 브레인스토밍 필요

## Phase: queued

### Community Sharing (Phase 1)

<!-- phase: queued | source_file: .claude/docs/later.md | source_line: 15 -->

GitHub repo (dotclaude-community) + CLI `install` command for sharing configs.
- Depends on: Knowledge Collector (provides ProjectProfile schema)

### Community Sharing (Phase 2-3)

<!-- phase: queued | source_file: .claude/docs/later.md | source_line: 19 -->

- Phase 2: opt-in ProjectProfile upload via `sync`
- Phase 3: server aggregation + recommendation API

### CLI Pull Command (서버→로컬 동기화)

<!-- phase: queued | source_file: .claude/docs/ideas.md | source_line: 20 -->

- 날짜: 2026-04-09
- 배경: 서버에 적재된 지식(추천 rules/agents 등)을 로컬에 반영하는 경로가 없음
- 개요: `dotclaude pull` — 서버 추천 설정을 로컬 ~/.claude/에 동기화. 개인 모드는 추천 기반, 팀 모드는 팀 표준 pull
- 열린 질문: 충돌 해결 전략 (서버가 source of truth, 로컬은 pull-only가 유력)
- 상태: Phase 3

### Evolve → RAG Upgrade

<!-- phase: queued | source_file: .claude/docs/ideas.md | source_line: 27 -->

- 날짜: 2026-04-09
- 배경: 현재 --evolve는 로컬 카탈로그 매칭. 서버에 팀 데이터가 쌓이면 추천 품질이 올라갈 수 있음
- 개요: 기존 rule-based evolve를 RAG 검색 기반으로 업그레이드. "이 스택에서 다른 사용자들은 이 설정을 쓴다" 수준의 추천
- 상태: Phase 2

### Code-Context Recommendations (코드 읽기 기반 추천)

<!-- phase: queued | source_file: .claude/docs/ideas.md | source_line: 66 -->

- 날짜: 2026-04-09
- 출처: later.md
- 배경: 현재 추천은 파일 확장자 패턴 매칭(카탈로그). 실제 코드를 읽으면 더 정확한 추천 가능
- 개요: claude-config 에이전트에 Level 1(파일 패턴) + Level 2(코드 샘플링) 적용. 카탈로그 매칭을 넘어 에이전트가 실제 코드를 읽고 맥락 파악
- 상태: Evolve → RAG Upgrade와 통합 검토

### PyPI Publish (패키지 이름 확정)

<!-- phase: queued | source_file: .claude/docs/ideas.md | source_line: 73 -->

- 날짜: 2026-04-09
- 출처: project_python_migration 메모리
- 배경: `dotclaude` 이름이 PyPI에서 타인이 선점 (v0.2.0). 대안 이름 확정 필요
- 개요: 이름 후보 결정 → PyPI 퍼블리시 → GitHub Actions CI 구성
- 상태: 외부 공개 결정 시 진행

### 클로드키우기 — CLI config_status 이름 목록 (Phase 0)

<!-- phase: queued | source_file: .claude/docs/ideas.md | source_line: 80 -->

- 날짜: 2026-04-09
- 출처: 과거 세션 (클로드키우기 아이디어)
- 배경: Evolution 시스템의 Phase 0. 서버에서 설정 변화 diff를 추출하려면 CLI가 config_status에 개별 에이전트/스킬/룰 이름 목록을 포함해서 보내야 함
- 개요: 현재 config_status는 카운트만 보냄 (agents: 5). 이름 목록도 추가 (agents: ["planner", "critic", ...]). 서버가 싱크 간 diff 계산 가능해짐
- 상태: Evolution 시스템 착수 시 진행

