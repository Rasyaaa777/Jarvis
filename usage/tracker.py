import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from config import MONTHLY_BUDGET, BUDGET_ALERT_THRESHOLD

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(_BASE_DIR, "data", "app.db")


def get_connection() -> sqlite3.Connection:
    """Returns a SQLite connection configured with WAL mode and a busy timeout to prevent locking issues."""
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE, timeout=15.0)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
    except Exception:
        pass
    return conn

def init_db():
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                provider TEXT,
                model TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                estimated_cost REAL,
                tool_called TEXT,
                latency_ms REAL,
                status TEXT,
                error_message TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS feedback_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                tag TEXT,
                comment TEXT
            )
        ''')
        conn.commit()
    finally:
        conn.close()

def log_usage(provider: str, model: str, input_tokens: int, output_tokens: int, estimated_cost: float, 
              tool_called: str = None, latency_ms: float = 0, status: str = "ok", error_message: str = None):
    init_db()
    conn = get_connection()
    try:
        c = conn.cursor()
        timestamp = datetime.now().isoformat()
        c.execute('''
            INSERT INTO usage_log (timestamp, provider, model, input_tokens, output_tokens, estimated_cost, tool_called, latency_ms, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, provider, model, input_tokens, output_tokens, estimated_cost, tool_called, latency_ms, status, error_message))
        conn.commit()
    finally:
        conn.close()

def log_feedback(tag: str, comment: Optional[str] = None):
    """Logs user satisfaction feedback ('good' or 'bad')."""
    init_db()
    conn = get_connection()
    try:
        c = conn.cursor()
        timestamp = datetime.now().isoformat()
        c.execute('INSERT INTO feedback_tags (timestamp, tag, comment) VALUES (?, ?, ?)', (timestamp, tag.lower(), comment))
        conn.commit()
    finally:
        conn.close()

def check_budget_status() -> Dict[str, Any]:
    """
    Calculates running spend in the current month against MONTHLY_BUDGET.
    Triggers alert when spend crosses the configured threshold (e.g. 80% or 100%).
    """
    init_db()
    conn = get_connection()
    try:
        c = conn.cursor()
        current_month = datetime.now().strftime("%Y-%m")
        c.execute('SELECT SUM(estimated_cost) FROM usage_log WHERE timestamp LIKE ?', (f"{current_month}%",))
        month_spend = c.fetchone()[0] or 0.0
    finally:
        conn.close()

    budget = MONTHLY_BUDGET
    pct = (month_spend / budget * 100) if budget > 0 else 0.0

    alert_level = "ok"
    alert_message = None

    if budget > 0 and month_spend >= budget:
        alert_level = "exceeded"
        alert_message = f"🚨 PERINGATAN: Pengeluaran bulan ini (${month_spend:.4f}) telah MELEBIHI batas anggaran bulanan (${budget:.2f})!"
    elif budget > 0 and (month_spend / budget) >= BUDGET_ALERT_THRESHOLD:
        alert_level = "warning"
        alert_message = f"⚠️ PERINGATAN: Pengeluaran bulan ini (${month_spend:.4f}) telah mencapai {pct:.1f}% dari batas anggaran (${budget:.2f})!"

    return {
        "monthly_budget": budget,
        "current_month_spend": month_spend,
        "percentage": round(pct, 1),
        "status": alert_level,
        "alert_message": alert_message
    }

def get_usage_summary() -> Dict[str, Any]:
    """Returns detailed KPIs, provider breakdown, budget tracking, and error metrics."""
    init_db()
    conn = get_connection()
    try:
        c = conn.cursor()
        
        # Total activity
        c.execute('SELECT COUNT(*) FROM usage_log')
        total_calls = c.fetchone()[0] or 0
        
        # Success / error counts
        c.execute("SELECT COUNT(*) FROM usage_log WHERE status = 'ok'")
        successful_calls = c.fetchone()[0] or 0
        failed_calls = total_calls - successful_calls
        error_rate = (failed_calls / total_calls * 100) if total_calls > 0 else 0.0
        
        # Tool calls & Tool success rate
        c.execute('SELECT COUNT(*) FROM usage_log WHERE tool_called IS NOT NULL')
        tool_calls = c.fetchone()[0] or 0
        c.execute("SELECT COUNT(*) FROM usage_log WHERE tool_called IS NOT NULL AND status = 'ok'")
        tool_calls_ok = c.fetchone()[0] or 0
        tool_success_rate = (tool_calls_ok / tool_calls * 100) if tool_calls > 0 else 100.0
        
        # Total Cost
        c.execute('SELECT SUM(estimated_cost) FROM usage_log')
        total_cost = c.fetchone()[0] or 0.0
        
        # Average Latency
        c.execute("SELECT AVG(latency_ms) FROM usage_log WHERE status = 'ok'")
        avg_latency = c.fetchone()[0] or 0.0

        # Provider breakdown
        c.execute('''
            SELECT provider, 
                   COUNT(*) as calls,
                   SUM(input_tokens) as in_tokens,
                   SUM(output_tokens) as out_tokens,
                   SUM(estimated_cost) as cost,
                   AVG(CASE WHEN status = 'ok' THEN latency_ms END) as avg_lat,
                   SUM(CASE WHEN status != 'ok' THEN 1 ELSE 0 END) as errors
            FROM usage_log
            GROUP BY provider
        ''')
        provider_rows = c.fetchall()
        providers = {}
        for row in provider_rows:
            providers[row[0]] = {
                "calls": row[1] or 0,
                "input_tokens": row[2] or 0,
                "output_tokens": row[3] or 0,
                "cost": row[4] or 0.0,
                "avg_latency": row[5] or 0.0,
                "errors": row[6] or 0
            }

        # Errors in last 1 hour
        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
        c.execute("SELECT COUNT(*) FROM usage_log WHERE status != 'ok' AND timestamp >= ?", (one_hour_ago,))
        errors_last_hour = c.fetchone()[0] or 0

        # Last call info
        c.execute("SELECT timestamp, provider, status FROM usage_log ORDER BY id DESC LIMIT 1")
        last_row = c.fetchone()
        last_call = {
            "timestamp": last_row[0] if last_row else "-",
            "provider": last_row[1] if last_row else "-",
            "status": last_row[2] if last_row else "-"
        }
        
        # Feedback summary
        c.execute("SELECT tag, COUNT(*) FROM feedback_tags GROUP BY tag")
        feedbacks = dict(c.fetchall())
    finally:
        conn.close()
    
    budget_info = check_budget_status()

    return {
        "total_calls": total_calls,
        "successful_calls": successful_calls,
        "failed_calls": failed_calls,
        "error_rate": round(error_rate, 2),
        "tool_calls": tool_calls,
        "tool_success_rate": round(tool_success_rate, 1),
        "total_cost": total_cost,
        "avg_latency": avg_latency,
        "providers": providers,
        "errors_last_hour": errors_last_hour,
        "last_call": last_call,
        "feedback": feedbacks,
        "budget": budget_info
    }


def get_recent_activity_logs(limit: int = 6) -> List[Dict[str, Any]]:
    """Returns the most recent API calls and tool interaction records."""
    init_db()
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('''
            SELECT id, timestamp, provider, model, tool_called, latency_ms, status, estimated_cost
            FROM usage_log
            ORDER BY id DESC
            LIMIT ?
        ''', (limit,))
        rows = c.fetchall()
        logs = []
        for r in rows:
            logs.append({
                "id": r[0],
                "timestamp": r[1],
                "provider": r[2],
                "model": r[3],
                "tool_called": r[4] or "-",
                "latency_ms": r[5] or 0.0,
                "status": r[6],
                "cost": r[7] or 0.0
            })
        return logs
    finally:
        conn.close()

