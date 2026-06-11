# ☕ Lumière Coffee — Sector Daily Logger

> A full-stack daily operations logger for a coffee shop SMB, built with Python and SQLite — zero external dependencies.

---

## What it does

Lumière Coffee is a web app that lets coffee shop staff log every order in real time and gives managers a live dashboard to track revenue, top-selling items, and daily trends.

Built as part of an internship project exploring how small businesses can replace manual spreadsheet logging with a lightweight, self-hosted web tool.

---

## Features

- **POS Order Screen** — tap menu items to build a ticket, set the date, and place the order in one click
- **Live Dashboard** — revenue, order count, items sold, and average order value — filterable by date or all-time
- **Bar Charts** — category breakdown, top 5 items, and last 30 days of daily revenue
- **Order History** — full log table with delete
- **Daily Report API** — end-of-day summary: total revenue, avg order, top item, category mix
- **Test Suite** — 12 automated API tests, zero pip installs needed

---

## Tech stack

| Layer     | Tech                                      |
|-----------|-------------------------------------------|
| Backend   | Python 3 — `http.server`, `sqlite3`       |
| Database  | SQLite (single file, auto-created)        |
| Frontend  | Vanilla JS SPA — no frameworks            |
| Tests     | Python `unittest` + `urllib`              |
| Deps      | **None** — runs on any machine with Python 3 |

The zero-dependency constraint was intentional: the app should run on any computer, in any environment, without a setup step.

---

## Quick start

```bash
git clone https://github.com/YOUR_USERNAME/lumiere-coffee
cd lumiere-coffee
python server.py
```

Then open **http://localhost:8000** in your browser.

> Always open via `http://localhost:8000` — not by double-clicking `index.html` — the browser needs to reach the API.

---

## API endpoints

| Method   | Endpoint                       | Description                             |
|----------|--------------------------------|-----------------------------------------|
| `POST`   | `/api/log`                     | Log a new order                         |
| `GET`    | `/api/summary?date=YYYY-MM-DD` | Aggregated stats (optional date filter) |
| `GET`    | `/api/orders?date=YYYY-MM-DD`  | List orders                             |
| `DELETE` | `/api/orders/:id`              | Delete an order                         |
| `GET`    | `/api/daily-report?date=`      | Full end-of-day report for one date     |

**Example — log an order:**
```bash
curl -X POST http://localhost:8000/api/log \
  -H "Content-Type: application/json" \
  -d '{"item":"Flat White","category":"Espresso","qty":2,"price":4.50}'
```

**Example — get today's summary:**
```bash
curl "http://localhost:8000/api/summary?date=2024-11-15"
```

---

## Running the tests

Start the server first, then in a second terminal:

```bash
python test_api.py
```

All 12 tests should pass in under a second.

---

## Project structure

```
lumiere-coffee/
├── server.py       # HTTP server + all API route handlers
├── index.html      # Single-page app (home / menu / order / dashboard)
├── test_api.py     # Full API test suite
├── CLAUDE.md       # Architecture notes and build plan
├── coffee.db       # SQLite database (auto-created on first run)
└── README.md       # This file
```

---

## What I'd add with more time

- User authentication (staff PIN login)
- Inventory tracking — deduct ingredients per order
- CSV export for the daily report
- Docker container for one-command deployment
- Multi-location support

---

## License

MIT
