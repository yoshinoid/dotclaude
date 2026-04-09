"""Insights command — rule-based signal detection + optional Gemini AI recommendations."""

from __future__ import annotations

import asyncio

import typer
from dotclaude_types.models import (
    GeminiInsightsResponse,
    InsightSignal,
)
from rich.console import Console

from dotclaude.insights import (
    GeminiError,
    build_gemini_payload,
    build_user_prompt,
    call_gemini,
    detect_locale,
    detect_signals,
    generate_recommendations,
    get_gemini_api_key,
    get_system_prompt,
)
from dotclaude.insights.merge import MergedRecommendation, merge_recommendations
from dotclaude.insights.server_recommendations import fetch_recommendations
from dotclaude.parser import analyze

_console = Console()
_err_console = Console(stderr=True)

_RULE_LABELS: dict[str, dict[str, str]] = {
    "cacheHitRate": {
        "ko": "캐시 히트율이 낮습니다",
        "en": "Low cache hit rate",
    },
    "agentUsage": {
        "ko": "서브에이전트를 거의 활용하지 않습니다",
        "en": "Subagents underutilized",
    },
    "hooks": {
        "ko": "훅이 설정되지 않았습니다",
        "en": "No hooks configured",
    },
    "rules": {
        "ko": "Rules 파일이 적습니다",
        "en": "Few rules configured",
    },
    "bashOveruse": {
        "ko": "Bash로 파일 검색을 과다하게 사용합니다",
        "en": "Bash overused for file search (use Glob/Grep tools)",
    },
    "commands": {
        "ko": "커스텀 커맨드가 없습니다",
        "en": "No custom commands configured",
    },
    "skills": {
        "ko": "스킬이 설정되지 않았습니다",
        "en": "No skills configured",
    },
    "mcp": {
        "ko": "MCP 서버가 설정되지 않았습니다",
        "en": "No MCP servers configured",
    },
    "missingStackRule": {
        "ko": "사용 중인 기술 스택에 맞는 rules 파일이 없습니다",
        "en": "Missing rules for actively used tech stack",
    },
}


def _severity_icon(severity: str) -> str:
    icons = {"error": "[red]\u2716[/red]", "warning": "[yellow]\u26a0[/yellow]", "info": "[cyan]\u2139[/cyan]"}
    return icons.get(severity, "\u2022")


def _grade_colored(grade: str) -> str:
    if grade in ("S", "A"):
        return f"[green]{grade}[/green]"
    if grade.startswith("B"):
        return f"[yellow]{grade}[/yellow]"
    return f"[red]{grade}[/red]"


def _render_fallback(signals: list[InsightSignal], locale: str) -> None:
    divider = "\u2500" * 50
    _console.print(f"\n[bold]{divider}[/bold]")
    header = "Claude Code 사용 패턴 분석" if locale == "ko" else "Usage Health Check"
    _console.print(f"[bold] {header}[/bold]")
    _console.print(f"[bold]{divider}[/bold]")

    if not signals:
        no_issues = (
            "감지된 비효율이 없습니다. 잘 활용하고 있습니다!"
            if locale == "ko"
            else "No inefficiencies detected. Great usage!"
        )
        _console.print(f"\n  [green]\u2714[/green]  {no_issues}")
    else:
        _console.print()
        for s in signals:
            label = _RULE_LABELS.get(s.rule, {}).get(locale, s.rule)
            _console.print(f"  {_severity_icon(s.severity)}  {label}")

    _console.print()
    tip = (
        "  \U0001f4a1 GEMINI_API_KEY를 설정하면 AI 기반 상세 추천을 받을 수 있습니다."
        if locale == "ko"
        else "  \U0001f4a1 Set GEMINI_API_KEY for AI-powered detailed recommendations."
    )
    _console.print(f"[dim]{tip}[/dim]")
    _console.print("[dim]     dotclaude config set-key <your-key>[/dim]")
    _console.print()


def _render_gemini_result(result: GeminiInsightsResponse, locale: str) -> None:
    divider = "\u2500" * 50
    _console.print(f"\n[bold]{divider}[/bold]")
    header = "Claude Code 사용 패턴 분석" if locale == "ko" else "Usage Health Check"
    _console.print(f"[bold] {header}[/bold]")
    _console.print(f"[bold]{divider}[/bold]")

    score_label = "활용도 점수" if locale == "ko" else "Health Score"
    _console.print(
        f"\n  {score_label}: {_grade_colored(result.grade)}  ({result.health_score}/100)\n"
    )

    for insight in result.insights:
        _console.print(
            f"  {_severity_icon(insight.severity)}  [bold]{insight.title}[/bold]"
        )
        _console.print(f"     [dim]{insight.description}[/dim]")
        _console.print(f"     [cyan]\u2192[/cyan] {insight.recommendation}")
        _console.print()

    _console.print(f"[bold]{divider}[/bold]")
    _console.print(f"  {result.summary}")
    _console.print()


def _render_merged_recommendations(
    merged: list[MergedRecommendation],
    server_count: int,
    local_count: int,
    locale: str,
) -> None:
    divider = "\u2500" * 50
    _console.print(f"\n[bold]{divider}[/bold]")
    header = (
        "Config Evolution \u2014 추천"
        if locale == "ko"
        else "Config Evolution \u2014 Recommendations"
    )
    _console.print(f"[bold] {header}[/bold]")
    _console.print(f"[bold]{divider}[/bold]")

    if not merged:
        no_recs = (
            "추가 추천 사항이 없습니다. 설정이 잘 되어 있습니다!"
            if locale == "ko"
            else "No recommendations. Your config is well-matched!"
        )
        _console.print(f"\n  [green]\u2714[/green]  {no_recs}")
        _console.print()
        return

    # Sub-header: source breakdown
    if server_count > 0 and local_count > 0:
        src_label = (
            f"서버 {server_count}개, 로컬 {local_count}개"
            if locale == "ko"
            else f"{server_count} from server, {local_count} from local"
        )
    elif server_count > 0:
        src_label = "서버 추천" if locale == "ko" else "from server"
    else:
        src_label = "로컬 추천" if locale == "ko" else "from local"

    _console.print(f"\n  [dim]Recommendations ({src_label})[/dim]\n")

    type_icons = {
        "agent": "[cyan]\u25c6[/cyan]",
        "rule": "[magenta]\u25c7[/magenta]",
        "hook": "[yellow]\u26a1[/yellow]",
        "skill": "[green]\u2605[/green]",
        "command": "[blue]\u25a0[/blue]",
    }

    # Column header
    _console.print(
        f"  [bold]{'Type':<8} {'Title':<22} {'Score':>6}  Source[/bold]"
    )
    _console.print(f"  {'─' * 46}")

    for rec in merged:
        icon = type_icons.get(rec.type, "\u00b7")
        score_str = f"{rec.score:.2f}" if rec.score is not None else "  -  "

        source_badge = "[cyan]\u25c6 server[/cyan]" if rec.source == "server" else "[dim]\u25cb local[/dim]"

        _console.print(
            f"  {icon} [dim]{rec.type:<7}[/dim] [bold]{rec.title:<22}[/bold]"
            f" {score_str:>6}  {source_badge}"
        )
        if rec.description:
            _console.print(f"            [dim]{rec.description}[/dim]")
        if rec.reason:
            _console.print(f"            [dim italic]{rec.reason}[/dim italic]")
        if rec.action_path:
            _console.print(
                f"            [cyan]\u2192[/cyan] [dim]{rec.action_path}[/dim]"
            )
        _console.print()

    agent_count = sum(1 for r in merged if r.type == "agent")
    rule_count = sum(1 for r in merged if r.type == "rule")
    summary = (
        f"  {len(merged)}개 추천 (agent: {agent_count}, rule: {rule_count})"
        if locale == "ko"
        else f"  {len(merged)} recommendations (agent: {agent_count}, rule: {rule_count})"
    )
    _console.print(f"[dim]{summary}[/dim]")
    disclaimer = (
        "  * 프로젝트 CLAUDE.md에 인라인으로 작성된 규칙은 감지가 제한적입니다"
        if locale == "ko"
        else "  * Rules inlined in project CLAUDE.md may not be fully detected"
    )
    _console.print(f"[dim]{disclaimer}[/dim]")
    _console.print()


def run_insights(path: str | None = None, evolve: bool = False) -> None:
    """Run the insights command.

    Args:
        path: Custom path to ~/.claude directory.
        evolve: If True, show config evolution recommendations instead of AI insights.
    """
    locale = detect_locale()
    analyze_msg = "분석 중..." if locale == "ko" else "Analyzing..."
    _err_console.print(f"[dim]{analyze_msg}[/dim]", end="\r")

    try:
        data = asyncio.run(analyze(path))
    except Exception as e:
        _err_console.print(
            f"[red]Error:[/red] Failed to analyze Claude directory.\n  {e}"
        )
        raise typer.Exit(1) from e

    _err_console.print("               ", end="\r")

    signals = detect_signals(data)

    if evolve:
        # 1. Fetch server recommendations (non-blocking — returns None on failure)
        fetch_msg = "서버 추천 가져오는 중..." if locale == "ko" else "Fetching server recommendations..."
        _err_console.print(f"[dim]{fetch_msg}[/dim]", end="\r")
        server_recs = fetch_recommendations()
        _err_console.print("                                        ", end="\r")

        # 2. Generate local catalog recommendations
        local_recs = generate_recommendations(data)

        # 3. Merge: server first, local as supplement
        merged, server_count, local_count = merge_recommendations(server_recs, local_recs)

        # 4. Render merged result
        _render_merged_recommendations(merged, server_count, local_count, locale)
        return

    api_key = get_gemini_api_key()

    if not api_key:
        _render_fallback(signals, locale)
        return

    gemini_msg = "AI 분석 중..." if locale == "ko" else "Getting AI insights..."
    _err_console.print(f"[dim]{gemini_msg}[/dim]", end="\r")

    payload = build_gemini_payload(data, signals)
    system_prompt = get_system_prompt(locale)
    user_prompt = build_user_prompt(payload, locale)

    try:
        gemini_result = asyncio.run(call_gemini(api_key, system_prompt, user_prompt))
    except GeminiError as e:
        _err_console.print()
        _err_console.print(f"[yellow]\u26a0  Gemini: {e}[/yellow]")
        fallback_msg = (
            "  룰 기반 분석으로 전환합니다."
            if locale == "ko"
            else "  Falling back to rule-based analysis."
        )
        _err_console.print(f"[dim]{fallback_msg}[/dim]")
        _render_fallback(signals, locale)
        return
    except Exception as e:
        _err_console.print()
        _err_console.print(f"[yellow]\u26a0  Unexpected error: {e}[/yellow]")
        _render_fallback(signals, locale)
        return

    _err_console.print("               ", end="\r")
    _render_gemini_result(gemini_result, locale)
