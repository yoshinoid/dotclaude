# dotclaude CLI — Roadmap
> Updated: 2026-04-09

## Active

### Knowledge Collector Agent
Periodically collect project context data and store structured profiles.
- Targets: tech stack, frameworks, project scale, conventions
- Output: `.claude/knowledge/project-profile.json`
- claude-config references this for better recommendations
- **Status:** Not started — brainstorming needed

## Backlog

### Community Sharing (Phase 1)
GitHub repo (dotclaude-community) + CLI `install` command for sharing configs.
- Depends on: Knowledge Collector (provides ProjectProfile schema)

### Community Sharing (Phase 2-3)
- Phase 2: opt-in ProjectProfile upload via `sync`
- Phase 3: server aggregation + recommendation API

### Code-Context Recommendations
claude-config agent Level 1 (file pattern) + Level 2 (code sampling).
- Move beyond catalog matching to actual code reading.

## Completed

### TypeScript to Python Migration
- Full CLI rewrite from TS to Python (2026-04-09)
- dotclaude-types extracted as shared package

### Mono-repo Split
- Split into CLI (public) + Server (private) repos (2026-04-09)
