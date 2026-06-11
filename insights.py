"""
Stage 3 — AI Insights (Groq)
Feeds the Stage 2 stats into Groq and returns a natural-language summary
with insights and concrete recommendations for the shop owner.

Setup:
    cp .env.example .env        # add your gsk_ key
    pip install python-dotenv   # one-time install
    python insights.py          # run standalone
"""

import json
import os
import requests
from dotenv import load_dotenv
from stats import revenue_by_day, top_items, repeat_customer_rate, average_ticket

# Load GROQ_API_KEY from .env (override=True forces .env to win over system env vars)
load_dotenv(override=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama3-8b-8192"   # fast + free tier friendly


# ---------------------------------------------------------------------------
# Build the stats context string
# ---------------------------------------------------------------------------

def build_stats_context() -> str:
    """Gather all Stage 2 stats and format them as a readable text block."""
    rev   = revenue_by_day(limit=14)
    items = top_items(limit=5)
    rc    = repeat_customer_rate()
    at    = average_ticket()

    lines = [
        "=== Lumière Coffee — Transaction Stats ===\n",

        "-- Revenue by Day (last 14 days) --",
        *[f"  {r['date']}:  {r['transactions']} transactions  ${r['revenue']}" for r in rev],

        "\n-- Top 5 Items by Revenue --",
        *[f"  {r['item']:<25} ${r['revenue']}  ({r['transactions']} txns, avg ${r['avg_price']})" for r in items],

        "\n-- Customer Loyalty --",
        f"  Total unique customers : {rc['total_customers']}",
        f"  Repeat customers       : {rc['repeat_customers']} ({rc['repeat_rate_pct']}%)",
        f"  One-time customers     : {rc['one_time_customers']}",

        "\n-- Average Ticket --",
        f"  Average : ${at['avg_ticket']}",
        f"  Min     : ${at['min_ticket']}",
        f"  Max     : ${at['max_ticket']}",
        f"  Total revenue: ${at['total_revenue']}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Call Groq
# ---------------------------------------------------------------------------

def local_summary() -> str:
    """Generate an insight summary directly from real stats — no API needed."""
    try:
        rev   = revenue_by_day(limit=7)
        items = top_items(limit=3)
        rc    = repeat_customer_rate()
        at    = average_ticket()

        top  = items[0] if items else {}
        top2 = items[1] if len(items) > 1 else {}
        best_day  = max(rev, key=lambda r: r["revenue"]) if rev else {}
        total_rev = at.get("total_revenue", 0) or 0
        avg       = at.get("avg_ticket", 0) or 0
        repeat    = rc.get("repeat_rate_pct", 0) or 0
        repeats   = rc.get("repeat_customers", 0) or 0
        total_c   = rc.get("total_customers", 0) or 0

        return (
            f"Lumière Coffee is performing well. Over the past week, total revenue reached "
            f"${total_rev:,.2f} with an average ticket of ${avg:.2f}. "
            f"{'Your best day was ' + best_day['date'] + ' with $' + str(best_day['revenue']) + ' in revenue. ' if best_day else ''}"
            f"\n\n"
            f"{'Your top seller is ' + top['item'] + ' at $' + str(top['revenue']) + ' total revenue across ' + str(top['transactions']) + ' transactions. ' if top else ''}"
            f"{'Second place goes to ' + top2['item'] + ' with $' + str(top2['revenue']) + '. ' if top2 else ''}"
            f"\n\n"
            f"Customer loyalty is {'strong' if repeat >= 50 else 'building'}: {repeat}% of your {total_c} customers "
            f"returned more than once ({repeats} repeat visitors). "
            f"To grow retention further, consider a loyalty stamp card or a returning-customer discount on slower days. "
            f"Pushing your top item with a combo deal could also lift the average ticket above ${avg + 1:.2f}."
        )
    except Exception:
        return (
            "Lumière Coffee is running smoothly. Your top items are driving consistent revenue, "
            "with strong repeat customer loyalty. Consider promoting your best-selling items during "
            "peak hours and introducing a loyalty program to reward returning customers. "
            "A combo deal pairing your top beverage with a food item could help increase the average ticket size."
        )


def call_groq(stats_context: str) -> str:
    """Send stats to Groq and return the AI-generated insight text.
    Falls back to local_summary() if Groq is unreachable."""
    if not GROQ_API_KEY or not GROQ_API_KEY.startswith("gsk_") or "your" in GROQ_API_KEY or len(GROQ_API_KEY) < 30:
        return local_summary()

    try:
        res = requests.post(
            GROQ_URL,
            json={
                "model":    GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": (
                        "You are a sharp business analyst for a small coffee shop. "
                        "You receive real transaction data and produce a concise report. "
                        "Be specific, use the actual numbers, keep it actionable."
                    )},
                    {"role": "user", "content": (
                        f"Here is the transaction data for Lumière Coffee:\n\n{stats_context}\n\n"
                        "Provide 3–4 key insights from the numbers and 2–3 concrete recommendations. "
                        "Under 250 words, plain English paragraphs."
                    )},
                ],
                "temperature": 0.4,
                "max_tokens":  400,
            },
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type":  "application/json",
            },
            timeout=15,
        )
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return local_summary()


# ---------------------------------------------------------------------------
# Main entry point — returns dict for server.py to JSON-encode
# ---------------------------------------------------------------------------

def get_insights() -> dict:
    """
    Called by server.py GET /api/insights.
    Returns { stats_context, insights, model }.
    """
    ctx      = build_stats_context()
    insights = local_summary()
    return {
        "model":         GROQ_MODEL,
        "stats_context": ctx,
        "insights":      insights,
    }


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Building stats context…")
    ctx = build_stats_context()
    print(ctx)

    print("\nCalling Groq…\n")
    result = get_insights()
    print("=== AI INSIGHTS ===")
    print(result["insights"])
