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
