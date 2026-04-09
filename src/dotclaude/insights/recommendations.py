"""Config evolution recommendation engine.

Analyzes per-project file activity, tech stack, and current config
to suggest missing agents, rules, hooks, and skills.
"""

from __future__ import annotations

from dotclaude.models import (
    CatalogEntry,
    CatalogRecommendation,
    DotClaudeData,
    Recommendation,
    CatalogDetect,
)

# ---------------------------------------------------------------------------
# Catalog — each entry maps a tech stack to recommended config items
# ---------------------------------------------------------------------------

CATALOG: list[CatalogEntry] = [
    CatalogEntry(
        id="python-backend",
        detect=CatalogDetect(extensions=[".py"], tech_stack=["python"]),
        recommendations=[
            CatalogRecommendation(
                type="rule",
                name="backend/python.md",
                description="Python coding conventions",
                rule_file="backend/python.md",
            ),
            CatalogRecommendation(
                type="rule",
                name="backend/async-patterns.md",
                description="Async/await patterns",
                rule_file="backend/async-patterns.md",
            ),
            CatalogRecommendation(
                type="agent",
                name="python-pro",
                description="Python backend specialist",
                agent_name="python-pro",
            ),
        ],
    ),
    CatalogEntry(
        id="typescript-frontend",
        detect=CatalogDetect(extensions=[".ts", ".tsx"], tech_stack=["node"]),
        recommendations=[
            CatalogRecommendation(
                type="rule",
                name="frontend/typescript.md",
                description="TypeScript strict conventions",
                rule_file="frontend/typescript.md",
            ),
            CatalogRecommendation(
                type="agent",
                name="typescript-pro",
                description="TypeScript specialist",
                agent_name="typescript-pro",
            ),
        ],
    ),
    CatalogEntry(
        id="react",
        detect=CatalogDetect(extensions=[".tsx", ".jsx"]),
        recommendations=[
            CatalogRecommendation(
                type="rule",
                name="frontend/react.md",
                description="React hooks and component patterns",
                rule_file="frontend/react.md",
            ),
            CatalogRecommendation(
                type="agent",
                name="react-specialist",
                description="React component specialist",
                agent_name="react-specialist",
            ),
        ],
    ),
    CatalogEntry(
        id="vue",
        detect=CatalogDetect(extensions=[".vue"]),
        recommendations=[
            CatalogRecommendation(
                type="rule",
                name="frontend/vue.md",
                description="Vue 3 Composition API patterns",
                rule_file="frontend/vue.md",
            ),
            CatalogRecommendation(
                type="agent",
                name="vue-expert",
                description="Vue/Nuxt specialist",
                agent_name="vue-expert",
            ),
        ],
    ),
    CatalogEntry(
        id="golang",
        detect=CatalogDetect(extensions=[".go"], tech_stack=["go"]),
        recommendations=[
            CatalogRecommendation(
                type="rule",
                name="backend/golang.md",
                description="Go idioms and error handling",
                rule_file="backend/golang.md",
            ),
            CatalogRecommendation(
                type="agent",
                name="golang-pro",
                description="Go backend specialist",
                agent_name="golang-pro",
            ),
        ],
    ),
    CatalogEntry(
        id="java-spring",
        detect=CatalogDetect(extensions=[".java"], tech_stack=["java"]),
        recommendations=[
            CatalogRecommendation(
                type="rule",
                name="backend/java-spring.md",
                description="Spring Boot conventions",
                rule_file="backend/java-spring.md",
            ),
            CatalogRecommendation(
                type="agent",
                name="spring-boot-engineer",
                description="Spring Boot specialist",
                agent_name="spring-boot-engineer",
            ),
        ],
    ),
    CatalogEntry(
        id="kotlin-android",
        detect=CatalogDetect(extensions=[".kt"], tech_stack=["kotlin"]),
        recommendations=[
            CatalogRecommendation(
                type="rule",
                name="mobile/android-kotlin.md",
                description="Android/Kotlin patterns",
                rule_file="mobile/android-kotlin.md",
            ),
            CatalogRecommendation(
                type="agent",
                name="kotlin-specialist",
                description="Kotlin/Android specialist",
                agent_name="kotlin-specialist",
            ),
        ],
    ),
    CatalogEntry(
        id="swift-ios",
        detect=CatalogDetect(extensions=[".swift"], tech_stack=["swift"]),
        recommendations=[
            CatalogRecommendation(
                type="rule",
                name="mobile/swift.md",
                description="Swift/SwiftUI patterns",
                rule_file="mobile/swift.md",
            ),
            CatalogRecommendation(
                type="agent",
                name="swift-expert",
                description="Swift/iOS specialist",
                agent_name="swift-expert",
            ),
        ],
    ),
    CatalogEntry(
        id="flutter",
        detect=CatalogDetect(extensions=[".dart"], tech_stack=["dart"]),
        recommendations=[
            CatalogRecommendation(
                type="rule",
                name="mobile/flutter.md",
                description="Flutter/Dart patterns",
                rule_file="mobile/flutter.md",
            ),
            CatalogRecommendation(
                type="agent",
                name="flutter-expert",
                description="Flutter specialist",
                agent_name="flutter-expert",
            ),
        ],
    ),
    CatalogEntry(
        id="rust",
        detect=CatalogDetect(extensions=[".rs"], tech_stack=["rust"]),
        recommendations=[
            CatalogRecommendation(
                type="agent",
                name="rust-specialist",
                description="Rust specialist",
                agent_name="rust-specialist",
            ),
        ],
    ),
    CatalogEntry(
        id="docker",
        detect=CatalogDetect(extensions=["Dockerfile"]),
        recommendations=[
            CatalogRecommendation(
                type="rule",
                name="devops/docker.md",
                description="Docker best practices",
                rule_file="devops/docker.md",
            ),
            CatalogRecommendation(
                type="agent",
                name="devops-engineer",
                description="Docker/CI/CD specialist",
                agent_name="devops-engineer",
            ),
        ],
    ),
    CatalogEntry(
        id="database",
        detect=CatalogDetect(extensions=[".sql"]),
        recommendations=[
            CatalogRecommendation(
                type="rule",
                name="db/common.md",
                description="Database query and index patterns",
                rule_file="db/common.md",
            ),
            CatalogRecommendation(
                type="agent",
                name="postgres-pro",
                description="PostgreSQL specialist",
                agent_name="postgres-pro",
            ),
        ],
    ),
]

_MAX_RECOMMENDATIONS = 5
_MIN_EXTENSION_COUNT = 5


# ---------------------------------------------------------------------------
# Matching engine
# ---------------------------------------------------------------------------


def _build_action_path(rec: CatalogRecommendation, claude_dir: str) -> str:
    """Build the full action path for a recommendation."""
    if rec.type == "rule" and rec.rule_file is not None:
        return f"{claude_dir}/rules/{rec.rule_file}".replace("\\", "/")
    if rec.type == "agent" and rec.agent_name is not None:
        return f"{claude_dir}/agents/{rec.agent_name}.md".replace("\\", "/")
    return f"{claude_dir}/{rec.type}s/{rec.name}".replace("\\", "/")


def _get_max_extension_count(entry: CatalogEntry, extensions: dict[str, int]) -> int:
    """Get the maximum file operation count for matching extensions."""
    max_count = 0
    for ext in entry.detect.extensions or []:
        count = extensions.get(ext, 0)
        if count > max_count:
            max_count = count
    return max_count


def _is_catalog_match(
    entry: CatalogEntry,
    extensions: dict[str, int],
    tech_stack: set[str],
) -> bool:
    """Check if a catalog entry matches the given tech stack and extensions."""
    if entry.detect.tech_stack is not None:
        for t in entry.detect.tech_stack:
            if t in tech_stack:
                return True

    if entry.detect.extensions is not None:
        for ext in entry.detect.extensions:
            if extensions.get(ext, 0) >= _MIN_EXTENSION_COUNT:
                return True

    return False


def _emit_recommendations(
    catalog_entry: CatalogEntry,
    extensions: dict[str, int],
    claude_md_keywords: set[str],
    project_name: str | None,
    existing_rules: set[str],
    existing_agents: set[str],
    seen: set[str],
    claude_dir: str,
    out: list[Recommendation],
) -> None:
    """Emit recommendations for a matched catalog entry."""
    max_count = _get_max_extension_count(catalog_entry, extensions)
    base_confidence: Recommendation.__class__  # type annotation hint

    if max_count >= 50:
        confidence: str = "high"
    elif max_count >= 15:
        confidence = "medium"
    else:
        confidence = "low"

    for rec in catalog_entry.recommendations:
        key = f"{rec.type}:{rec.name}"
        if key in seen:
            continue

        # Skip if already configured
        if rec.type == "rule" and rec.rule_file is not None and rec.rule_file in existing_rules:
            continue
        if (
            rec.type == "agent"
            and rec.agent_name is not None
            and rec.agent_name in existing_agents
        ):
            continue

        # Lower confidence if CLAUDE.md mentions related keywords
        adjusted_confidence = confidence
        if claude_md_keywords:
            entry_keywords = [catalog_entry.id] + list(catalog_entry.detect.tech_stack or [])
            has_overlap = any(k in claude_md_keywords for k in entry_keywords)
            if has_overlap and adjusted_confidence != "low":
                adjusted_confidence = "medium" if adjusted_confidence == "high" else "low"

        seen.add(key)
        reason = (
            f"{project_name} uses {catalog_entry.id} stack"
            if project_name is not None
            else f"{catalog_entry.id} stack detected globally"
        )

        out.append(
            Recommendation(
                catalog_id=catalog_entry.id,
                type=rec.type,
                name=rec.name,
                description=rec.description,
                reason=reason,
                project=project_name,
                confidence=adjusted_confidence,  # type: ignore[arg-type]
                action_path=_build_action_path(rec, claude_dir),
            )
        )


def _match_catalog_for_project(
    extensions: dict[str, int],
    tech_stack: set[str],
    claude_md_keywords: set[str],
    project_name: str,
    existing_rules: set[str],
    existing_agents: set[str],
    seen: set[str],
    claude_dir: str,
    out: list[Recommendation],
) -> None:
    for entry in CATALOG:
        if not _is_catalog_match(entry, extensions, tech_stack):
            continue
        _emit_recommendations(
            entry,
            extensions,
            claude_md_keywords,
            project_name,
            existing_rules,
            existing_agents,
            seen,
            claude_dir,
            out,
        )


def _match_catalog_global(
    extensions: dict[str, int],
    tech_stack: set[str],
    claude_md_keywords: set[str],
    existing_rules: set[str],
    existing_agents: set[str],
    seen: set[str],
    claude_dir: str,
    out: list[Recommendation],
) -> None:
    for entry in CATALOG:
        if not _is_catalog_match(entry, extensions, tech_stack):
            continue
        _emit_recommendations(
            entry,
            extensions,
            claude_md_keywords,
            None,
            existing_rules,
            existing_agents,
            seen,
            claude_dir,
            out,
        )


def generate_recommendations(data: DotClaudeData) -> list[Recommendation]:
    """Generate recommendations by matching project profiles against the catalog.

    Checks both global (~/.claude/) and project-level (.claude/) config.
    Returns at most MAX_RECOMMENDATIONS (5) items sorted by confidence.
    """
    recommendations: list[Recommendation] = []
    global_rules: set[str] = set(data.config_status.rules.files or [])
    global_agents: set[str] = set(data.config_status.agents.names)
    seen: set[str] = set()

    for project in data.projects:
        if project.breakdown is None and project.tech_stack is None:
            continue

        extensions: dict[str, int] = project.breakdown.file_extensions if project.breakdown else {}
        tech_stack: set[str] = set(project.tech_stack or [])
        project_name = project.decoded_path or project.encoded_path

        project_rules: set[str] = set(project.project_config.rules if project.project_config else [])
        project_agents: set[str] = set(
            project.project_config.agents if project.project_config else []
        )
        claude_md_keywords: set[str] = set(
            project.project_config.claude_md_keywords if project.project_config else []
        )

        all_rules = global_rules | project_rules
        all_agents = global_agents | project_agents

        _match_catalog_for_project(
            extensions,
            tech_stack,
            claude_md_keywords,
            project_name,
            all_rules,
            all_agents,
            seen,
            data.meta.claude_dir,
            recommendations,
        )

    # Also check global file activity as fallback
    if data.file_activity is not None:
        all_tech_stacks: set[str] = set()
        all_claude_md_keywords: set[str] = set()
        for project in data.projects:
            for t in project.tech_stack or []:
                all_tech_stacks.add(t)
            if project.project_config:
                for k in project.project_config.claude_md_keywords:
                    all_claude_md_keywords.add(k)
        _match_catalog_global(
            data.file_activity.by_extension,
            all_tech_stacks,
            all_claude_md_keywords,
            global_rules,
            global_agents,
            seen,
            data.meta.claude_dir,
            recommendations,
        )

    # Sort by confidence (high first), then type
    order = {"high": 0, "medium": 1, "low": 2}
    recommendations.sort(key=lambda r: order.get(r.confidence, 2))

    return recommendations[:_MAX_RECOMMENDATIONS]
