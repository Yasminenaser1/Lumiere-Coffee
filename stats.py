"""
Stage 2 — Stats Pipeline
Four functions that query the transactions table.
Stage 4 reuses these directly as agent tools.

Usage:
    from stats import revenue_by_day, top_items, repeat_customer_rate, average_ticket
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.expanduser("~"), "coffee.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# 1. Revenue by day
# ---------------------------------------------------------------------------

def revenue_by_day(limit: int = 30) -> list[dict]:
    """
    Returns total revenue per day, most recent first.
    Each dict: { date, transactions, revenue }
    """
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                date,
                COUNT(*)              AS transactions,
                ROUND(SUM(amount), 2) AS revenue
            FROM transactions
            GROUP BY date
            ORDER BY date DESC
            LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# 2. Top items
# ---------------------------------------------------------------------------

def top_items(limit: int = 5) -> list[dict]:
    """
    Returns best-selling items ranked by total revenue.
    Each dict: { item, transactions, revenue, avg_price }
    """
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                item,
                COUNT(*)               AS transactions,
                ROUND(SUM(amount), 2)  AS revenue,
                ROUND(AVG(amount), 2)  AS avg_price
            FROM transactions
            GROUP BY item
            ORDER BY revenue DESC
            LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# 3. Repeat-customer rate
# ---------------------------------------------------------------------------

def repeat_customer_rate() -> dict:
    """
    Returns the percentage of customers who visited more than once.
    Dict: { total_customers, repeat_customers, one_time_customers, repeat_rate_pct }
    """
    with get_db() as conn:
        rows = conn.execute("""
            SELECT customer_id, COUNT(*) AS visits
            FROM transactions
            GROUP BY customer_id
        """).fetchall()

    total    = len(rows)
    repeats  = sum(1 for r in rows if r["visits"] > 1)
    one_time = total - repeats
    rate     = round((repeats / total * 100), 1) if total else 0

    return {
        "total_customers":   total,
        "repeat_customers":  repeats,
        "one_time_customers": one_time,
        "repeat_rate_pct":   rate,
    }


# ---------------------------------------------------------------------------
# 4. Average ticket
# ---------------------------------------------------------------------------

def average_ticket() -> dict:
    """
    Returns average transaction value and related totals.
    Dict: { total_transactions, total_revenue, avg_ticket, min_ticket, max_ticket }
    """
    with get_db() as conn:
        row = conn.execute("""
            SELECT
                COUNT(*)              AS total_transactions,
                ROUND(SUM(amount), 2) AS total_revenue,
                ROUND(AVG(amount), 2) AS avg_ticket,
                ROUND(MIN(amount), 2) AS min_ticket,
                ROUND(MAX(amount), 2) AS max_ticket
            FROM transactions
        """).fetchone()
    return dict(row) if row else {}


# ---------------------------------------------------------------------------
# Quick self-test — run directly: python stats.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== Revenue by Day (last 7) ===")
    for r in revenue_by_day(limit=7):
        print(f"  {r['date']}  {r['transactions']} txns  ${r['revenue']}")

    print("\n=== Top Items ===")
    for r in top_items():
        print(f"  {r['item']:<25} ${r['revenue']}  ({r['transactions']} txns, avg ${r['avg_price']})")

    print("\n=== Repeat Customer Rate ===")
    rc = repeat_customer_rate()
    print(f"  {rc['repeat_customers']}/{rc['total_customers']} customers returned ({rc['repeat_rate_pct']}%)")

    print("\n=== Average Ticket ===")
    at = average_ticket()
    print(f"  Avg: ${at['avg_ticket']}  |  Min: ${at['min_ticket']}  |  Max: ${at['max_ticket']}  |  Total: ${at['total_revenue']}")
