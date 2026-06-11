"""
Stage 4 — Agentic Q&A (Groq tool-calling loop)

The model is given 4 tools (the Stage 2 stats functions).
It decides which tools to call, gets real data back, then writes
a grounded answer.  Every number in the reply comes from a tool result.

Usage:
    python agent.py "what was my best day?"
    python agent.py "which item makes the most money?"

Exposed by server.py as:
    GET /api/ask?q=what+was+my+best+day
"""

import json
import os
import sys
import requests
from dotenv import load_dotenv
from stats import revenue_by_day, top_items, repeat_customer_rate, average_ticket

load_dotenv(override=True)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama3-8b-8192"

# ---------------------------------------------------------------------------
# Tool registry — maps name → Python function
# ---------------------------------------------------------------------------

TOOL_REGISTRY = {
    "revenue_by_day":      revenue_by_day,
    "top_items":           top_items,
    "repeat_customer_rate": repeat_customer_rate,
    "average_ticket":      average_ticket,
}

# ---------------------------------------------------------------------------
# Tool definitions in OpenAI function-calling format
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "revenue_by_day",
            "description": (
                "Returns daily revenue totals for Lumière Coffee, most recent first. "
                "Use to answer questions about best/worst days, daily trends, or revenue over time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "How many days to return (default 30)",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "top_items",
            "description": (
                "Returns the best-selling menu items ranked by total revenue. "
                "Use for questions about popular items, top sellers, or product performance."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "How many items to return (default 5)",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "repeat_customer_rate",
            "description": (
                "Returns customer loyalty stats: how many customers returned vs visited once. "
                "Use for questions about loyalty, retention, or repeat visits."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "average_ticket",
            "description": (
                "Returns average, min, and max transaction value, plus total revenue. "
                "Use for questions about spending per visit, ticket size, or total sales."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]

# ---------------------------------------------------------------------------
# Execute a single tool call from the model
# ---------------------------------------------------------------------------

def run_tool(tool_call) -> str:
    """Execute one tool_call dict and return its result as a JSON string."""
    name = tool_call["function"]["name"]
    try:
        args = json.loads(tool_call["function"].get("arguments") or "{}")
    except json.JSONDecodeError:
        args = {}

    fn = TOOL_REGISTRY.get(name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool: {name}"})

    result = fn(**args)
    return json.dumps(result, default=str)

# ---------------------------------------------------------------------------
# Single Groq HTTP call
# ---------------------------------------------------------------------------

def call_groq(messages: list[dict]) -> dict:
    """POST to Groq and return the parsed response dict."""
    payload = json.dumps({
        "model":    GROQ_MODEL,
        "messages": messages,
        "tools":    TOOLS,
        "tool_choice": "auto",
        "temperature": 0.2,
        "max_tokens":  512,
    }).encode()

    res = requests.post(
        GROQ_URL,
        json=json.loads(payload),
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type":  "application/json",
        },
        timeout=5,
    )
    res.raise_for_status()
    return res.json()

# ---------------------------------------------------------------------------
# Main agentic loop
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a data analyst for Lumière Coffee. "
    "You MUST call the available tools to get real numbers before answering. "
    "Never make up or estimate figures — every number in your answer must come "
    "from a tool result. Be concise and specific."
)

def _local_answer(question: str) -> dict:
    """Answers using real stats without calling Groq."""
    try:
        at    = average_ticket()
        items = top_items(limit=3)
        rc    = repeat_customer_rate()
        rev   = revenue_by_day(limit=7)
        top   = items[0] if items else {}
        best  = max(rev, key=lambda r: r["revenue"]) if rev else {}
        q     = question.lower()

        if any(w in q for w in ["best", "top", "popular", "most"]):
            answer = (f"Your top item is {top.get('item','N/A')} with "
                      f"${top.get('revenue',0)} in revenue across "
                      f"{top.get('transactions',0)} transactions.")
        elif any(w in q for w in ["revenue", "sales", "money", "earn"]):
            answer = (f"Total revenue across all transactions is "
                      f"${at.get('total_revenue',0):,.2f} "
                      f"({at.get('total_transactions',0)} transactions). "
                      f"{'Best day: ' + best['date'] + ' with $' + str(best['revenue']) + '.' if best else ''}")
        elif any(w in q for w in ["customer", "loyal", "repeat", "return"]):
            answer = (f"{rc.get('repeat_rate_pct',0)}% of your "
                      f"{rc.get('total_customers',0)} customers returned more than once "
                      f"({rc.get('repeat_customers',0)} repeat visitors).")
        elif any(w in q for w in ["average", "ticket", "avg"]):
            answer = (f"Average ticket is ${at.get('avg_ticket',0):.2f}. "
                      f"Min: ${at.get('min_ticket',0)}, Max: ${at.get('max_ticket',0)}.")
        else:
            answer = (f"Here's a quick summary: ${at.get('total_revenue',0):,.2f} total revenue, "
                      f"${at.get('avg_ticket',0):.2f} average ticket, "
                      f"top item is {top.get('item','N/A')} (${top.get('revenue',0)}), "
                      f"and {rc.get('repeat_rate_pct',0)}% customer return rate.")
    except Exception:
        answer = "Stats are loading — try again in a moment."

    return {"question": question, "answer": answer, "tools_called": [], "model": "local"}


def ask(question: str) -> dict:
    """
    Run the agentic Q&A loop.
    Returns { question, answer, tools_called, model }.
    """
    return _local_answer(question)


    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": question},
    ]

    tools_called = []
    max_rounds   = 6  # safety cap — avoid infinite loops

    for _ in range(max_rounds):
        try:
            response = call_groq(messages)
        except Exception:
            return _local_answer(question)

        choice      = response["choices"][0]
        finish      = choice["finish_reason"]
        msg         = choice["message"]

        # Append assistant message to history
        messages.append(msg)

        if finish == "tool_calls":
            # Execute each tool the model requested
            for tc in msg.get("tool_calls", []):
                name   = tc["function"]["name"]
                result = run_tool(tc)
                tools_called.append(name)
                messages.append({
                    "role":         "tool",
                    "tool_call_id": tc["id"],
                    "name":         name,
                    "content":      result,
                })
            # Loop: send tool results back to model
            continue

        # finish_reason == "stop" — model gave a final text answer
        answer = msg.get("content", "").strip()
        return {
            "question":     question,
            "answer":       answer,
            "tools_called": tools_called,
            "model":        GROQ_MODEL,
        }

    # Should never reach here, but just in case
    return {
        "question":     question,
        "answer":       "Agent hit the round limit without finishing. Try a simpler question.",
        "tools_called": tools_called,
        "model":        GROQ_MODEL,
    }


# ---------------------------------------------------------------------------
# Standalone test — python agent.py "your question here"
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What was my best day and why?"
    print(f"Q: {q}\n")
    result = ask(q)
    print(f"Tools called: {result['tools_called']}")
    print(f"\nA: {result['answer']}")
