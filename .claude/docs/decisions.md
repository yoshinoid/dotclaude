# Technical Decisions

## Python over TypeScript for CLI
- **Decision:** Rewrite CLI from TypeScript to Python
- **Why:** Simpler deployment (no Node.js required), direct Pydantic model sharing with FastAPI server, better cross-platform support for data analysis tooling
- **Alternatives:** Keep TypeScript (rejected — dual-language type sync burden)

## Separate dotclaude-types package
- **Decision:** Extract Pydantic models into standalone `dotclaude-types` package
- **Why:** CLI and server both need the same types. Extracting early prevents import path changes later. Structurally prevents server from importing CLI code.
- **Alternatives:** extras (e.g., `dotclaude[types]`) — rejected because splitting gets harder as package grows

## orjson for JSONL parsing
- **Decision:** Use orjson instead of stdlib json
- **Why:** JSONL files can be 100MB+; orjson is 2-10x faster for parsing
- **Alternatives:** stdlib json (simpler, but slower on large files). Benchmark pending (task 5).

## camelCase aliases on all models
- **Decision:** All Pydantic models use `alias_generator=to_camel`
- **Why:** REST API and stored JSON use camelCase (inherited from TypeScript era). Python code uses snake_case via `populate_by_name=True`.
- **Alternatives:** Rename all JSON keys to snake_case (rejected — breaking change for existing snapshots in DB)

## Backward-compat re-export shim
- **Decision:** Keep `dotclaude.models` as a re-export of `dotclaude_types.models`
- **Why:** Any external code importing from `dotclaude.models` won't break
- **Alternatives:** Hard removal (too aggressive for v0.x)

## dotclaude-rag 별도 레포 (Phase 1, 2026-04-09)
- **Decision:** RAG 엔진(frontmatter, chunker, embedding, signals)을 별도 레포로 분리
- **Why:** CLI와 Server 양쪽에서 사용. CLI는 frontmatter 포매터 용도, Server는 chunker+embedding+signals 재계산 용도. types처럼 계약 공유
- **Alternatives:** CLI 내부 모듈 (rejected — server가 CLI 코드를 import하는 역방향 의존 발생)

## Server-side content_hash 재계산 (Phase 1, 리뷰 후)
- **Decision:** Knowledge 업로드 시 서버에서 content를 SHA-256으로 재해시하여 dedup
- **Why:** 클라이언트가 전달한 content_hash를 신뢰하면 조작 가능. 동일 content에 다른 hash를 보내면 dedup 우회
- **Alternatives:** 클라이언트 값 신뢰 (rejected — 보안 취약)

## --evolve 서버+로컬 병합 전략 (Phase 2)
- **Decision:** 서버 추천 우선, 로컬 카탈로그는 서버 결과에 없는 것만 보충 (title+type 조합으로 dedup, max 7)
- **Why:** 서버 추천은 실제 사용 데이터 기반 개인화됨. 로컬 카탈로그는 오프라인 폴백 + 기본 커버리지
- **Alternatives:** 로컬만 (기존 동작), 서버만 (오프라인 불가)

## LangGraph Plan B — 자체 상태 머신 (Phase 3b)
- **Decision:** LangGraph 대신 자체 WorkflowRun 테이블 기반 상태 머신 구현
- **Why:** LangGraph checkpointer가 psycopg3 사용, 기존 SQLModel+asyncpg와 드라이버 충돌. 두 커넥션 풀 공존 복잡도가 이득을 초과
- **Alternatives:** langgraph-checkpoint-postgres (드라이버 공존 복잡도), 비동기 태스크 큐 (과잉 설계)
- **Trade-off:** interrupt/resume 기능 포기. 대신 CLI 폴링으로 동일한 UX 구현

## Pull path traversal 방지 (Phase 3b, 보안)
- **Decision:** CLI safe_write에서 `resolve() + is_relative_to(base_dir)` 검증
- **Why:** 서버가 target_path를 제어하므로, 악성 서버 또는 조작된 응답이 `../../..` 경로를 보내면 사용자 시스템 파일 덮어쓰기 가능
- **Alternatives:** 서버만 신뢰 (rejected — 공격 표면)

## Team Knowledge dedup index — COALESCE 트릭 (Phase 3a)
- **Decision:** `UNIQUE (user_id, COALESCE(team_id, zero_uuid), content_hash)`
- **Why:** 같은 사용자가 같은 파일을 개인+팀에 모두 업로드할 수 있어야 함. PostgreSQL NULL 비교는 UNIQUE 제약에서 허용이므로 COALESCE로 NULL → 고정 UUID 변환
- **Alternatives:** 별도 team_knowledge 테이블 (벡터 검색 JOIN 복잡도 증가)

## 항상 리뷰 후 완료 (세션 피드백)
- **Decision:** spec/plan/구현 완료 후 반드시 /review 실행
- **Why:** Phase 1-3 모두 리뷰에서 Critical 이슈 발견됨. 리뷰 없이 "완료" 선언하면 프로덕션 위험
- **Sources:** feedback_always_review.md 메모리
