# ☕ Lumière Coffee — AI Customer-Insights Agent

> Turns a coffee shop's transaction data into AI-powered insights and an agentic Q&A that answers questions grounded in real numbers.

**Live demo:** https://lumiere-coffee.onrender.com  
**GitHub:** https://github.com/Yasminenaser1/Lumiere-Coffee

---

## What it does (one sentence)

Lumière Coffee ingests a shop's transaction history, runs a stats pipeline to surface revenue trends, top items, and customer loyalty, then uses Groq AI to generate plain-English insights and answer free-text questions — all through a live dashboard.

---

## Architecture (6 stages)

```
transactions.csv
      │
      ▼
Stage 1 — Data Ingest (load_csv.py)
      SQLite: transactions(id, date, item, amount, customer_id)
      │
      ▼
Stage 2 — Stats Pipeline (stats.py)
      revenue_by_day · top_items · repeat_customer_rate · average_ticket
      │
      ▼
Stage 3 — AI Insights (insights.py + Groq)
      Natural-language summary with actionable recommendations
      │
      ▼
Stage 4 — Agentic Q&A (agent.py)
      Tool-calling loop — answers grounded in real stats, not hallucinated
      │
      ▼
Stage 5 — Dashboard (index.html)
      Charts · stat cards · "Ask a question" box
      │
      ▼
Stage 6 — Tests + Deploy (test_api.py · Render)
      12 automated tests · live public URL
```

---

## Tech stack

| Layer     | Tech                                          |
|-----------|-----------------------------------------------|
| Backend   | Python 3 stdlib — `http.server`, `sqlite3`    |
| Database  | SQLite (single file, auto-created)            |
| AI        | Groq API (llama3-8b-8192) via `groq` SDK      |
| Frontend  | Vanilla JS SPA — Chart.js + Recharts          |
| Tests     | Python `unittest` + `urllib` (zero pip)       |
| Deploy    | Render (free tier)                            |

---

## Quick start

```bash
git clone https://github.com/Yasminenaser1/Lumiere-Coffee
cd Lumiere-Coffee

# 1 — add your Groq key
cp .env.example .env
# edit .env and set GROQ_API_KEY=gsk_...

# 2 — load sample data
python load_csv.py

# 3 — start the server
python server.py
```

Then open **http://localhost:8000** in your browser.

> Always open via `http://localhost:8000` — not by double-clicking `index.html`.

---

## Environment variables

```
GROQ_API_KEY=gsk_...   # required for AI insights and Q&A
```

Add `.env` to `.gitignore` — never commit API keys.

---

## API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/orders` | Log a new order |
| `GET` | `/api/orders?date=` | List orders |
| `GET` | `/api/stats?date=` | Aggregated dashboard stats |
| `GET` | `/api/stats/revenue-by-day` | Revenue per day (last 30) |
| `GET` | `/api/stats/top-items` | Best-selling items by revenue |
| `GET` | `/api/stats/repeat-customers` | Repeat customer rate |
| `GET` | `/api/stats/average-ticket` | Avg / min / max transaction value |
| `GET` | `/api/insights` | AI-generated summary (Groq) |
| `GET` | `/api/ask?q=` | Agentic Q&A — tool-calling loop |
| `GET` | `/api/daily-report?date=` | End-of-day manager report |
| `DELETE` | `/api/orders/:id` | Delete an order |

---

## Project structure

```
lumiere-coffee/
├── server.py          # HTTP server + all API route handlers
├── index.html         # Single-page app (home / menu / order / dashboard / AI)
├── stats.py           # Stage 2 — stats pipeline (4 functions)
├── insights.py        # Stage 3 — Groq AI summary
├── agent.py           # Stage 4 — tool-calling Q&A agent
├── load_csv.py        # Stage 1 — CSV → SQLite ingest
├── transactions.csv   # 200 realistic sample transactions
├── test_api.py        # 12 automated API tests
├── Dockerfile         # Container config for deployment
├── requirements.txt   # python-dotenv, requests, groq
├── .env               # API keys (never committed)
├── .gitignore
└── README.md
```

---

## Running the tests

Start the server first, then in a second terminal:

```bash
python test_api.py
```

---

## Demo

Visit **https://lumiere-coffee.onrender.com** and:
1. Go to **AI Insights** — see live stat cards and revenue/top-items charts
2. Type a question in the Ask box — e.g. *"What was my best day?"*
3. Go to **Dashboard** — filter by date, see order history
4. Go to **Order** — tap items, place an order, see it appear in the dashboard

---

## License

MIT
