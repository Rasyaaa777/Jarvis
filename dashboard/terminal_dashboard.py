import os
import sys

# Ensure project root is on sys.path
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE_DIR not in sys.path:
    sys.path.insert(0, _BASE_DIR)

# Ensure UTF-8 stdout on Windows
if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from usage.tracker import get_usage_summary

def show_dashboard():
    console = Console()
    summary = get_usage_summary()
    
    # ── 1. Header & Budget Alert ──────────────────────────────────────────────
    console.print()
    console.rule("[bold cyan]JARVIS AI - Activity & Cost Dashboard[/bold cyan]")
    console.print()

    budget = summary.get("budget", {})
    if budget.get("alert_message"):
        alert_style = "bold red on white" if budget.get("status") == "exceeded" else "bold yellow on black"
        console.print(Panel(f"[bold]{budget['alert_message']}[/bold]", style=alert_style, box=box.HEAVY))
        console.print()

    # ── 2. Top KPI Cards ──────────────────────────────────────────────────────
    total_calls = summary["total_calls"]
    total_cost = summary["total_cost"]
    month_spend = budget.get("current_month_spend", 0.0)
    monthly_budget = budget.get("monthly_budget", 5.0)
    pct = budget.get("percentage", 0.0)
    avg_latency = summary["avg_latency"]
    error_rate = summary["error_rate"]
    tool_success = summary["tool_success_rate"]

    kpi_table = Table(box=box.ROUNDED, expand=True)
    kpi_table.add_column("Total Calls", justify="center", style="cyan")
    kpi_table.add_column("Tool Success", justify="center", style="green")
    kpi_table.add_column("Avg Latency", justify="center", style="yellow")
    kpi_table.add_column("Error Rate", justify="center", style="red" if error_rate > 5 else "green")
    kpi_table.add_column("Month Spend", justify="center", style="magenta")

    kpi_table.add_row(
        f"[bold]{total_calls}[/bold] ({summary['successful_calls']} ok)",
        f"[bold]{tool_success:.1f}%[/bold] ({summary['tool_calls']} calls)",
        f"[bold]{avg_latency:.1f} ms[/bold]",
        f"[bold]{error_rate:.1f}%[/bold] ({summary['failed_calls']} fail)",
        f"[bold]${month_spend:.4f}[/bold] / ${monthly_budget:.2f} ({pct:.1f}%)"
    )
    console.print(Panel(kpi_table, title="[bold white]Executive Overview & KPIs[/bold white]", border_style="cyan"))

    # ── 3. Provider Breakdown Table ───────────────────────────────────────────
    prov_table = Table(title="LLM Provider Breakdown", box=box.SIMPLE_HEAVY, expand=True)
    prov_table.add_column("Provider", style="bold cyan")
    prov_table.add_column("Calls", justify="right")
    prov_table.add_column("In Tokens", justify="right")
    prov_table.add_column("Out Tokens", justify="right")
    prov_table.add_column("Est. Cost", justify="right", style="green")
    prov_table.add_column("Avg Latency", justify="right")
    prov_table.add_column("Errors", justify="right", style="red")

    providers = summary.get("providers", {})
    if providers:
        for p_name, p_data in providers.items():
            prov_table.add_row(
                p_name.upper(),
                str(p_data["calls"]),
                f"{p_data['input_tokens']:,}",
                f"{p_data['output_tokens']:,}",
                f"${p_data['cost']:.5f}",
                f"{p_data['avg_latency']:.1f} ms" if p_data['avg_latency'] else "-",
                str(p_data["errors"])
            )
    else:
        prov_table.add_row("No activity recorded", "-", "-", "-", "$0.00", "-", "0")

    console.print(prov_table)
    console.print()

    # ── 4. Infrastructure Health & Feedback ───────────────────────────────────
    last_call = summary.get("last_call", {})
    last_ts = last_call.get("timestamp", "-")
    last_prov = last_call.get("provider", "-")
    last_stat = last_call.get("status", "-")
    stat_color = "green" if last_stat == "ok" else "red"

    feedback = summary.get("feedback", {})
    good_fb = feedback.get("good", 0)
    bad_fb = feedback.get("bad", 0)

    health_text = (
        f"- Last API Call: {last_ts} ({last_prov.upper()}) -> [{stat_color}]{last_stat.upper()}[/{stat_color}]\n"
        f"- Errors in last 1 hour: [red]{summary['errors_last_hour']}[/red]\n"
        f"- User Feedback: [green]+{good_fb} good[/green] | [red]-{bad_fb} bad[/red]\n"
        f"- All-time Total Spend: [bold green]${total_cost:.4f}[/bold green]"
    )
    console.print(Panel(health_text, title="[bold white]Infrastructure Health & Status[/bold white]", border_style="blue"))
    console.print()

    # ── 5. Phase 3.5: Recent Activity & Tool Interaction Logs ─────────────────
    from usage.tracker import get_recent_activity_logs
    recent_logs = get_recent_activity_logs(limit=6)

    log_table = Table(title="Recent Activity & Tool Interaction Logs", box=box.ROUNDED, expand=True)
    log_table.add_column("Time", style="dim", justify="center")
    log_table.add_column("Provider / Model", style="cyan")
    log_table.add_column("Tool Executed", style="yellow")
    log_table.add_column("Latency", justify="right", style="magenta")
    log_table.add_column("Status", justify="center")
    log_table.add_column("Cost", justify="right", style="green")

    if recent_logs:
        for item in recent_logs:
            ts_short = item["timestamp"].split("T")[-1][:8] if "T" in item["timestamp"] else item["timestamp"]
            s_color = "green" if item["status"] == "ok" else "red"
            log_table.add_row(
                ts_short,
                f"{item['provider'].upper()} ({item['model']})",
                item["tool_called"],
                f"{item['latency_ms']:.0f} ms" if item["latency_ms"] else "-",
                f"[{s_color}]{item['status'].upper()}[/{s_color}]",
                f"${item['cost']:.5f}"
            )
    else:
        log_table.add_row("-", "-", "No recent activity", "-", "-", "$0.00")

    console.print(log_table)
    console.print()

if __name__ == "__main__":
    show_dashboard()

