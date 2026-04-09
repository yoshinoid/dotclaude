"""Rich-based dashboard renderer for the dotclaude CLI.

Renders all sections in a single terminal view using rich for colors and tables.
"""

from __future__ import annotations

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from dotclaude.display.formatters import (
    format_bar,
    format_cost,
    format_date,
    format_duration,
    format_number,
    format_percent,
    format_seconds,
    format_sparkline,
    format_tokens,
    short_model,
)
from dotclaude.models import DotClaudeData

_console = Console()


def _truncate(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def render_dashboard(data: DotClaudeData, top: int | None = None) -> None:
    """Render the dotclaude dashboard to the terminal using rich.

    Args:
        data: The analyzed DotClaudeData.
        top: Optional limit for items per section.
    """
    console = _console
    tool_limit = top or 10
    project_limit = top or 5

    # Title
    title = Text()
    title.append("dotclaude", style="bold cyan")
    title.append(" -- ", style="dim")
    title.append("Claude Code Usage Analyzer", style="white")
    console.print(Panel(title, expand=False))

    # -- Overview --
    summary = data.summary
    cost_estimate = data.cost_estimate

    ov_table = Table.grid(padding=(0, 2))
    ov_table.add_column()
    ov_table.add_column()
    ov_table.add_column()
    ov_table.add_row(
        f"[green]{format_number(summary.total_sessions)}[/green] sessions",
        f"[green]{format_number(summary.total_prompts)}[/green] prompts",
        f"[green]{format_number(summary.days_active)}[/green] days active",
    )
    ov_table.add_row(
        f"Total cost: [yellow]{format_cost(cost_estimate.total)}[/yellow]",
        f"Period: [white]{format_duration(summary.first_activity, summary.last_activity)}[/white]",
        "",
    )
    console.print(Panel(ov_table, title="[bold]Overview[/bold]"))

    # -- Tool Usage --
    tool_entries = sorted(data.tool_usage.items(), key=lambda x: x[1], reverse=True)[
        :tool_limit
    ]

    if tool_entries:
        tool_table = Table(show_header=False, box=None, padding=(0, 1))
        tool_table.add_column(width=14)
        tool_table.add_column(width=22)
        tool_table.add_column(width=6, justify="right")
        max_count = tool_entries[0][1]
        for name, count in tool_entries:
            bar = format_bar(count, max_count, 20)
            tool_table.add_row(
                f"[white]{_truncate(name, 14)}[/white]",
                f"[cyan]{bar}[/cyan]",
                f"[green]{count}[/green]",
            )
        console.print(Panel(tool_table, title=f"[bold]Tool Usage (top {tool_limit})[/bold]"))

    # -- File Activity --
    if data.file_activity:
        ext_entries = sorted(
            data.file_activity.by_extension.items(), key=lambda x: x[1], reverse=True
        )[:tool_limit]
        if ext_entries:
            ext_table = Table(show_header=False, box=None, padding=(0, 1))
            ext_table.add_column(width=14)
            ext_table.add_column(width=22)
            ext_table.add_column(width=6, justify="right")
            max_ext = ext_entries[0][1]
            for ext, count in ext_entries:
                bar = format_bar(count, max_ext, 20)
                ext_table.add_row(
                    f"[white]{_truncate(ext, 14)}[/white]",
                    f"[magenta]{bar}[/magenta]",
                    f"[green]{count}[/green]",
                )
            console.print(
                Panel(ext_table, title=f"[bold]File Types (top {tool_limit})[/bold]")
            )

    # -- Token & Cost by Model --
    if data.token_usage:
        model_table = Table(box=None, padding=(0, 1))
        model_table.add_column("Model", style="dim", width=14)
        model_table.add_column("Input", width=10)
        model_table.add_column("Output", width=10)
        model_table.add_column("Cache", width=10)
        model_table.add_column("Cost")

        cost_by_model = {m.model: m.cost for m in cost_estimate.by_model}
        for usage in data.token_usage:
            model_table.add_row(
                short_model(usage.model),
                f"[green]{format_tokens(usage.input_tokens)}[/green]",
                f"[green]{format_tokens(usage.output_tokens)}[/green]",
                f"[green]{format_tokens(usage.cache_creation_tokens + usage.cache_read_tokens)}[/green]",
                f"[yellow]{format_cost(cost_by_model.get(usage.model, 0.0))}[/yellow]",
            )
        console.print(Panel(model_table, title="[bold]Token & Cost by Model[/bold]"))

    # -- Top Projects --
    top_projects = sorted(data.projects, key=lambda p: p.session_count, reverse=True)[
        :project_limit
    ]
    if top_projects:
        proj_table = Table(show_header=False, box=None, padding=(0, 1))
        proj_table.add_column(width=30)
        proj_table.add_column()
        proj_table.add_column()
        for project in top_projects:
            display_path = _truncate(project.decoded_path or project.encoded_path, 30)
            sessions_text = (
                f"[green]{project.session_count:3d}[/green] [dim]sessions[/dim]"
            )
            last_seen = f"[dim]last:[/dim] [white]{format_date(project.last_activity)}[/white]"
            proj_table.add_row(
                f"[white]{display_path}[/white]",
                sessions_text,
                last_seen,
            )
            # Tech stack and top extensions
            details: list[str] = []
            if project.tech_stack:
                details.append(
                    " ".join(f"[cyan]{t}[/cyan]" for t in project.tech_stack)
                )
            if project.breakdown:
                top_exts = sorted(
                    project.breakdown.file_extensions.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:3]
                if top_exts:
                    details.append(
                        " ".join(
                            f"[magenta]{ext}[/magenta][dim]:[/dim][green]{cnt}[/green]"
                            for ext, cnt in top_exts
                        )
                    )
            if details:
                proj_table.add_row("  " + "  |  ".join(details), "", "")

        console.print(Panel(proj_table, title="[bold]Top Projects[/bold]"))

    # -- Config Status --
    cfg = data.config_status
    cfg_table = Table.grid(padding=(0, 2))
    cfg_table.add_column()
    cfg_table.add_column()
    cfg_table.add_column()
    cfg_table.add_column()
    cfg_table.add_row(
        f"Agents: [green]{cfg.agents.count}[/green]",
        f"Commands: [green]{cfg.commands.count}[/green]",
        f"Hooks: [green]{cfg.hooks.total_hooks}[/green]",
        f"Rules: [green]{cfg.rules.count}[/green]",
    )
    cfg_table.add_row(
        f"Skills: [green]{cfg.skills.count}[/green]",
        f"Plugins: [green]{cfg.plugins.marketplace_count}[/green]",
        f"MCP: [green]{cfg.mcp_servers.count}[/green]",
        "",
    )
    console.print(Panel(cfg_table, title="[bold]Config Status[/bold]"))

    # -- Subagent Usage --
    subagent_entries = sorted(
        data.subagent_stats.by_type.items(), key=lambda x: x[1], reverse=True
    )
    if subagent_entries:
        parts = "  |  ".join(
            f"[white]{t}[/white]: [green]{c}[/green]"
            for t, c in subagent_entries[:5]
        )
        console.print(Panel(Text.from_markup(parts), title="[bold]Subagent Usage[/bold]"))

    # -- Daily Cost Sparkline --
    if len(cost_estimate.by_day) > 1:
        costs = [d.cost for d in cost_estimate.by_day]
        sparkline = format_sparkline(costs, 70)
        first_date = cost_estimate.by_day[0].date if cost_estimate.by_day else ""
        last_date = cost_estimate.by_day[-1].date if cost_estimate.by_day else ""
        min_cost = min(costs)
        max_cost_val = max(costs)
        avg_cost = sum(costs) / len(costs)

        spark_table = Table.grid()
        spark_table.add_column()
        spark_table.add_row(f"[yellow]{sparkline}[/yellow]")
        spark_table.add_row(
            f"[dim]{first_date}[/dim]"
            + " " * max(1, 70 - len(first_date) - len(last_date))
            + f"[dim]{last_date}[/dim]"
        )
        spark_table.add_row(
            f"[dim]min:[/dim] [yellow]{format_cost(min_cost)}[/yellow]"
            f"  [dim]max:[/dim] [yellow]{format_cost(max_cost_val)}[/yellow]"
            f"  [dim]avg:[/dim] [yellow]{format_cost(avg_cost)}[/yellow]"
        )
        console.print(Panel(spark_table, title="[bold]Daily Cost Trend[/bold]"))

    # -- Session Duration --
    if data.session_durations.count > 0:
        sd = data.session_durations
        sd_table = Table.grid(padding=(0, 2))
        sd_table.add_column()
        sd_table.add_column()
        sd_table.add_column()
        sd_table.add_column()
        sd_table.add_row(
            f"[green]{sd.count}[/green] sessions",
            f"avg: [green]{format_seconds(sd.average_seconds)}[/green]",
            f"max: [green]{format_seconds(sd.max_seconds)}[/green]",
            f"total: [green]{format_seconds(sd.total_seconds)}[/green]",
        )
        console.print(Panel(sd_table, title="[bold]Session Duration[/bold]"))

    # -- Cache Performance --
    if data.cache_stats.total_input_tokens > 0:
        cs = data.cache_stats
        cs_table = Table.grid(padding=(0, 2))
        cs_table.add_column()
        cs_table.add_column()
        cs_table.add_column()
        cs_table.add_row(
            f"Hit rate: [green]{format_percent(cs.hit_rate)}[/green]",
            f"Read: [green]{format_tokens(cs.cache_read_tokens)}[/green]",
            f"Write: [green]{format_tokens(cs.cache_creation_tokens)}[/green]",
        )
        console.print(Panel(cs_table, title="[bold]Cache Performance[/bold]"))

    # -- Hook Execution Frequency --
    hook_limit = top or 8
    if data.hook_frequency.hooks:
        hook_table = Table(show_header=False, box=None, padding=(0, 1))
        hook_table.add_column(width=28)
        hook_table.add_column(width=12, style="dim")
        hook_table.add_column(width=18)
        hook_table.add_column(width=8, justify="right")

        hooks_to_show = data.hook_frequency.hooks[:hook_limit]
        max_runs = hooks_to_show[0].estimated_runs if hooks_to_show else 1
        for hook in hooks_to_show:
            bar = format_bar(hook.estimated_runs, max_runs, 16)
            hook_table.add_row(
                f"[white]{_truncate(hook.command, 28)}[/white]",
                hook.event[:10],
                f"[magenta]{bar}[/magenta]",
                f"[green]{format_number(hook.estimated_runs)}[/green]",
            )
        hook_table.add_row(
            f"[dim]Total estimated:[/dim] [green]{format_number(data.hook_frequency.total_estimated_runs)}[/green]",
            "",
            "",
            "",
        )
        console.print(
            Panel(
                hook_table,
                title="[bold]Hook Execution Frequency (estimated)[/bold]",
            )
        )

    # -- Entry Points --
    entrypoint_entries = sorted(
        data.process_stats.by_entrypoint.items(), key=lambda x: x[1], reverse=True
    )
    if entrypoint_entries:
        total_ep = sum(v for _, v in entrypoint_entries)
        parts_ep = "  |  ".join(
            f"[white]{name}[/white]: [green]{round(count / total_ep * 100) if total_ep else 0}%[/green]"
            for name, count in entrypoint_entries[:4]
        )
        console.print(Panel(Text.from_markup(parts_ep), title="[bold]Entry Points[/bold]"))
