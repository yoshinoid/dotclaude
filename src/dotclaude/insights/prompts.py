"""Prompt templates for Gemini API.

Uses JSON mode (response_mime_type: application/json) for reliable parsing.
"""

from __future__ import annotations

import json

from dotclaude.insights.anonymize import GeminiPayload

_JSON_SCHEMA = """{
  "healthScore": <integer 0-100>,
  "grade": <"S"|"A"|"B+"|"B"|"C+"|"C"|"D">,
  "insights": [
    {
      "severity": <"error"|"warning"|"info">,
      "title": <string>,
      "description": <string>,
      "recommendation": <string>
    }
  ],
  "summary": <string, 1-2 sentences>
}"""

_GLOSSARY_KO = """
## Claude Code 용어 정의 (반드시 이 정의를 사용하세요)
- agents: ~/.claude/agents/에 정의된 특수 목적 서브에이전트. 복잡한 작업을 위임할 때 사용
- hooks: Claude Code 이벤트(툴 실행 전후, 세션 종료 등)에 자동 실행되는 쉘 스크립트
- rules: ~/.claude/rules/의 도메인별 코딩 컨벤션 파일 (Python, TypeScript, Docker 등)
- commands: /commit, /review 등 사용자 정의 슬래시 커맨드
- skills: 특정 작업 패턴에 대한 가이드 문서
- MCP: Model Context Protocol의 약자. GitHub, Slack, DB 등 외부 툴/서비스를 Claude Code에 연결하는 서버. "Multi-Code Project"가 아님
- cacheHitRate: 이전 프롬프트 컨텍스트를 캐시에서 재사용하는 비율. 높을수록 비용 절감
- agentRatio: 전체 프롬프트 중 서브에이전트를 호출한 비율"""

_GLOSSARY_EN = """
## Claude Code Glossary (use these exact definitions)
- agents: Specialized sub-agents defined in ~/.claude/agents/ for delegating complex tasks
- hooks: Shell scripts that auto-run on Claude Code events (before/after tool use, session end, etc.)
- rules: Domain-specific coding convention files in ~/.claude/rules/ (Python, TypeScript, Docker, etc.)
- commands: User-defined slash commands like /commit, /review
- skills: Guidance documents for specific task patterns
- MCP: Stands for Model Context Protocol. Servers that connect external tools/services (GitHub, Slack, DB, etc.) to Claude Code. NOT "Multi-Code Project"
- cacheHitRate: Ratio of prompt context reused from cache. Higher = lower cost
- agentRatio: Fraction of total prompts that invoked a sub-agent"""

_SYSTEM_PROMPT_KO = f"""당신은 Claude Code 사용 패턴을 분석하는 전문가입니다.
사용자의 Claude Code 사용 통계를 분석하여 비효율적인 부분을 찾고 구체적인 개선 방법을 추천해주세요.
{_GLOSSARY_KO}

## 평가 기준
- healthScore는 0-100으로 Claude Code를 얼마나 잘 활용하고 있는지를 나타냅니다
- grade: S(95+) A(85+) B+(75+) B(65+) C+(55+) C(45+) D(미만)
- daysActive가 7 미만이면 초기 사용자로 보고 점수에 관대하게 반영하세요
- insights는 감지된 신호를 바탕으로 실용적인 추천을 제공하세요

반드시 아래 JSON 스키마로만 응답하세요:
{_JSON_SCHEMA}"""

_SYSTEM_PROMPT_EN = f"""You are an expert analyzing Claude Code usage patterns.
Analyze the provided Claude Code usage statistics to identify inefficiencies and recommend concrete improvements.
{_GLOSSARY_EN}

## Scoring Guidelines
- healthScore (0-100) reflects how effectively the user leverages Claude Code
- grade: S(95+) A(85+) B+(75+) B(65+) C+(55+) C(45+) D(below)
- If daysActive < 7, treat the user as early-stage and be generous with scoring
- insights should provide practical, actionable recommendations based on the detected signals

Respond ONLY with JSON matching this schema:
{_JSON_SCHEMA}"""


def get_system_prompt(locale: str) -> str:
    """Return the system prompt for the given locale."""
    return _SYSTEM_PROMPT_KO if locale == "ko" else _SYSTEM_PROMPT_EN


def build_user_prompt(payload: GeminiPayload, locale: str) -> str:
    """Build the user prompt with the anonymized payload."""
    label = (
        "다음은 Claude Code 사용 데이터입니다:"
        if locale == "ko"
        else "Here is the Claude Code usage data:"
    )
    return f"{label}\n\n{json.dumps(payload.to_dict(), indent=2, ensure_ascii=False)}"
