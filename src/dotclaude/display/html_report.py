"""Self-contained HTML report generator for dotclaude.

Produces a single HTML file with embedded CSS — no external dependencies.
"""

from __future__ import annotations

from dotclaude_types.models import DotClaudeData

from dotclaude.display.formatters import (
    format_cost,
    format_number,
    format_percent,
    format_seconds,
    format_tokens,
    short_model,
)


def _escape_html(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def _svg_bar_chart(entries: list[dict[str, object]], color: str) -> str:
    """Render an SVG horizontal bar chart."""
    if not entries:
        return ""
    max_val = max(float(e["value"]) for e in entries)  # type: ignore[arg-type]
    bar_h = 24
    gap = 4
    label_w = 140
    bar_max_w = 300
    value_w = 80
    total_w = label_w + bar_max_w + value_w + 20
    total_h = len(entries) * (bar_h + gap) + gap

    bars = []
    for i, entry in enumerate(entries):
        y = i * (bar_h + gap) + gap
        w = (float(entry["value"]) / max_val * bar_max_w) if max_val > 0 else 0  # type: ignore[arg-type]
        label = _escape_html(str(entry["label"]))
        value_str = format_number(int(entry["value"]))  # type: ignore[arg-type]
        bars.append(
            f'<text x="{label_w - 8}" y="{y + bar_h - 6}" text-anchor="end" fill="#ccc" font-size="13">{label}</text>'
            f'<rect x="{label_w}" y="{y}" width="{w:.1f}" height="{bar_h}" rx="3" fill="{color}" opacity="0.85"/>'
            f'<text x="{label_w + bar_max_w + 8}" y="{y + bar_h - 6}" fill="#aaa" font-size="13">{value_str}</text>'
        )

    bars_html = "".join(bars)
    return f'<svg width="{total_w}" height="{total_h}" xmlns="http://www.w3.org/2000/svg">{bars_html}</svg>'


def _svg_sparkline(values: list[float], width: int, height: int) -> str:
    """Render an SVG sparkline chart."""
    if len(values) < 2:
        return ""
    min_v = min(values)
    max_v = max(values)
    value_range = max_v - min_v or 1
    step = width / (len(values) - 1)

    points = " ".join(
        f"{i * step:.1f},{height - ((v - min_v) / value_range * (height - 10)) - 5:.1f}"
        for i, v in enumerate(values)
    )
    last_x = (len(values) - 1) * step
    area_points = f"0,{height} {points} {last_x:.1f},{height}"

    return (
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
        f'<polygon points="{area_points}" fill="rgba(234,179,8,0.15)"/>'
        f'<polyline points="{points}" fill="none" stroke="#eab308" stroke-width="2"/>'
        f"</svg>"
    )


def render_html(data: DotClaudeData) -> str:
    """Render a self-contained HTML report for the given DotClaudeData."""
    summary = data.summary
    cost_estimate = data.cost_estimate
    token_usage = data.token_usage
    cache_stats = data.cache_stats
    session_durations = data.session_durations
    hook_frequency = data.hook_frequency

    # Tool usage chart
    tool_entries = [
        {"label": label, "value": value}
        for label, value in sorted(data.tool_usage.items(), key=lambda x: x[1], reverse=True)[
            :15
        ]
    ]
    tool_chart = _svg_bar_chart(tool_entries, "#06b6d4")

    # File activity chart
    file_activity_entries = (
        [
            {"label": label, "value": value}
            for label, value in sorted(
                data.file_activity.by_extension.items(), key=lambda x: x[1], reverse=True
            )[:15]
        ]
        if data.file_activity
        else []
    )
    file_activity_chart = _svg_bar_chart(file_activity_entries, "#a855f7")

    # Cost by model chart
    cost_entries = [
        {"label": short_model(m.model), "value": round(m.cost * 100)}
        for m in cost_estimate.by_model
        if m.cost > 0
    ]
    cost_chart = _svg_bar_chart(cost_entries, "#eab308")

    # Daily cost sparkline
    daily_costs = [d.cost for d in cost_estimate.by_day]
    sparkline = _svg_sparkline(daily_costs, 600, 80)
    first_date = cost_estimate.by_day[0].date if cost_estimate.by_day else ""
    last_date = cost_estimate.by_day[-1].date if cost_estimate.by_day else ""

    # Projects table
    top_projects = sorted(data.projects, key=lambda p: p.session_count, reverse=True)[:10]
    project_rows_parts = []
    for p in top_projects:
        badges: list[str] = []
        if p.tech_stack:
            for t in p.tech_stack:
                badges.append(
                    f'<span style="background:#1e293b;color:#06b6d4;padding:2px 6px;'
                    f'border-radius:3px;font-size:11px">{_escape_html(t)}</span>'
                )
        if p.breakdown:
            top_exts = sorted(
                p.breakdown.file_extensions.items(), key=lambda x: x[1], reverse=True
            )[:3]
            for ext, _ in top_exts:
                badges.append(
                    f'<span style="color:#a855f7;font-size:11px">{_escape_html(ext)}</span>'
                )
        badge_html = f'<div style="margin-top:2px">{" ".join(badges)}</div>' if badges else ""
        display_path = _escape_html(p.decoded_path or p.encoded_path)
        project_rows_parts.append(
            f"<tr><td>{display_path}{badge_html}</td>"
            f"<td>{p.session_count}</td>"
            f"<td>{p.last_activity[:10]}</td></tr>"
        )
    project_rows = "".join(project_rows_parts)

    # Token table
    cost_by_model = {m.model: m.cost for m in cost_estimate.by_model}
    token_rows = "".join(
        f"<tr><td>{_escape_html(short_model(u.model))}</td>"
        f"<td>{format_tokens(u.input_tokens)}</td>"
        f"<td>{format_tokens(u.output_tokens)}</td>"
        f"<td>{format_tokens(u.cache_read_tokens)}</td>"
        f"<td>{format_cost(cost_by_model.get(u.model, 0.0))}</td></tr>"
        for u in token_usage
    )

    # Hook frequency table
    hook_rows = "".join(
        f"<tr><td>{_escape_html(h.command)}</td>"
        f"<td>{_escape_html(h.event)}</td>"
        f"<td>{_escape_html(h.matcher or '*')}</td>"
        f"<td>{format_number(h.estimated_runs)}</td></tr>"
        for h in hook_frequency.hooks[:10]
    )

    cfg = data.config_status
    filters = data.meta.filters
    since_str = f" | Since: {filters.since}" if filters and filters.since else ""
    until_str = f" | Until: {filters.until}" if filters and filters.until else ""

    session_dur_html = ""
    if session_durations.count > 0:
        session_dur_html = (
            '<div class="section"><h2>Session Duration</h2><div class="grid">'
            f'<div class="stat-card"><div class="label">Sessions Measured</div>'
            f'<div class="value">{session_durations.count}</div></div>'
            f'<div class="stat-card"><div class="label">Average</div>'
            f'<div class="value">{format_seconds(session_durations.average_seconds)}</div></div>'
            f'<div class="stat-card"><div class="label">Longest</div>'
            f'<div class="value">{format_seconds(session_durations.max_seconds)}</div></div>'
            f'<div class="stat-card"><div class="label">Total Time</div>'
            f'<div class="value">{format_seconds(session_durations.total_seconds)}</div></div>'
            "</div></div>"
        )

    tool_chart_html = (
        f'<div class="section"><h2>Tool Usage (top 15)</h2>{tool_chart}</div>'
        if tool_chart
        else ""
    )
    file_activity_html = (
        f'<div class="section"><h2>File Types (top 15)</h2>{file_activity_chart}</div>'
        if file_activity_chart
        else ""
    )
    cost_chart_html = (
        f'<div class="section"><h2>Cost by Model</h2>{cost_chart}'
        f'<p style="color:var(--dim);font-size:12px;margin-top:8px">Values in cents</p></div>'
        if cost_chart
        else ""
    )
    sparkline_html = (
        f'<div class="section"><h2>Daily Cost Trend</h2>{sparkline}'
        f'<div class="sparkline-dates"><span>{first_date}</span><span>{last_date}</span></div></div>'
        if sparkline
        else ""
    )
    hook_rows_html = (
        f'<div class="section"><h2>Hook Execution Frequency (estimated)</h2>'
        f"<table><thead><tr><th>Hook</th><th>Event</th><th>Matcher</th><th>Est. Runs</th></tr></thead>"
        f"<tbody>{hook_rows}</tbody></table>"
        f'<p style="color:var(--dim);font-size:12px;margin-top:8px">'
        f"Total: ~{format_number(hook_frequency.total_estimated_runs)} estimated executions</p></div>"
        if hook_rows
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>dotclaude Report</title>
<style>
  :root {{ --bg: #0f172a; --card: #1e293b; --border: #334155; --text: #e2e8f0; --dim: #94a3b8; --accent: #06b6d4; --green: #22c55e; --yellow: #eab308; }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, monospace; background: var(--bg); color: var(--text); padding: 24px; line-height: 1.6; }}
  .container {{ max-width: 900px; margin: 0 auto; }}
  h1 {{ color: var(--accent); font-size: 28px; margin-bottom: 8px; }}
  .subtitle {{ color: var(--dim); margin-bottom: 32px; font-size: 14px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 32px; }}
  .stat-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }}
  .stat-card .label {{ color: var(--dim); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }}
  .stat-card .value {{ font-size: 24px; font-weight: bold; color: var(--green); margin-top: 4px; }}
  .stat-card .value.yellow {{ color: var(--yellow); }}
  .stat-card .value.cyan {{ color: var(--accent); }}
  .section {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 24px; margin-bottom: 24px; }}
  .section h2 {{ color: var(--text); font-size: 18px; margin-bottom: 16px; border-bottom: 1px solid var(--border); padding-bottom: 8px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ text-align: left; color: var(--dim); font-weight: 500; padding: 8px 12px; border-bottom: 1px solid var(--border); }}
  td {{ padding: 8px 12px; border-bottom: 1px solid var(--border); color: var(--text); }}
  tr:hover td {{ background: rgba(255,255,255,0.03); }}
  .sparkline-dates {{ display: flex; justify-content: space-between; color: var(--dim); font-size: 12px; margin-top: 4px; }}
  .config-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 8px; }}
  .config-item {{ text-align: center; padding: 12px; background: var(--bg); border-radius: 6px; }}
  .config-item .num {{ font-size: 20px; font-weight: bold; color: var(--green); }}
  .config-item .name {{ color: var(--dim); font-size: 12px; margin-top: 2px; }}
  .footer {{ text-align: center; color: var(--dim); font-size: 12px; margin-top: 32px; padding-top: 16px; border-top: 1px solid var(--border); }}
  svg {{ display: block; max-width: 100%; }}
  @media (max-width: 600px) {{ .grid {{ grid-template-columns: 1fr 1fr; }} }}
</style>
</head>
<body>
<div class="container">
  <h1>dotclaude Report</h1>
  <div class="subtitle">Generated {data.meta.scanned_at[:10]}{since_str}{until_str}</div>

  <div class="grid">
    <div class="stat-card"><div class="label">Sessions</div><div class="value">{format_number(summary.total_sessions)}</div></div>
    <div class="stat-card"><div class="label">Prompts</div><div class="value">{format_number(summary.total_prompts)}</div></div>
    <div class="stat-card"><div class="label">Days Active</div><div class="value">{format_number(summary.days_active)}</div></div>
    <div class="stat-card"><div class="label">Total Cost</div><div class="value yellow">{format_cost(cost_estimate.total)}</div></div>
    <div class="stat-card"><div class="label">Cache Hit Rate</div><div class="value cyan">{format_percent(cache_stats.hit_rate)}</div></div>
    <div class="stat-card"><div class="label">Avg Session</div><div class="value">{format_seconds(session_durations.average_seconds) if session_durations.count > 0 else "&mdash;"}</div></div>
  </div>

  {tool_chart_html}
  {file_activity_html}

  <div class="section">
    <h2>Token &amp; Cost by Model</h2>
    <table>
      <thead><tr><th>Model</th><th>Input</th><th>Output</th><th>Cache Read</th><th>Cost</th></tr></thead>
      <tbody>{token_rows or '<tr><td colspan="5" style="color:var(--dim)">No data</td></tr>'}</tbody>
    </table>
  </div>

  {cost_chart_html}
  {sparkline_html}

  <div class="section">
    <h2>Top Projects</h2>
    <table>
      <thead><tr><th>Project</th><th>Sessions</th><th>Last Activity</th></tr></thead>
      <tbody>{project_rows or '<tr><td colspan="3" style="color:var(--dim)">No projects</td></tr>'}</tbody>
    </table>
  </div>

  {hook_rows_html}

  <div class="section">
    <h2>Config Status</h2>
    <div class="config-grid">
      <div class="config-item"><div class="num">{cfg.agents.count}</div><div class="name">Agents</div></div>
      <div class="config-item"><div class="num">{cfg.commands.count}</div><div class="name">Commands</div></div>
      <div class="config-item"><div class="num">{cfg.hooks.total_hooks}</div><div class="name">Hooks</div></div>
      <div class="config-item"><div class="num">{cfg.rules.count}</div><div class="name">Rules</div></div>
      <div class="config-item"><div class="num">{cfg.skills.count}</div><div class="name">Skills</div></div>
      <div class="config-item"><div class="num">{cfg.plugins.marketplace_count}</div><div class="name">Plugins</div></div>
      <div class="config-item"><div class="num">{cfg.mcp_servers.count}</div><div class="name">MCP Servers</div></div>
    </div>
  </div>

  {session_dur_html}

  <div class="footer">
    Generated by <strong>dotclaude</strong> v{data.meta.version} &mdash; Claude Code Usage Analyzer
  </div>
</div>
</body>
</html>"""
