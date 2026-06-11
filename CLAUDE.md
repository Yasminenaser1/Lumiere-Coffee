# ☕ Coffee Shop — Sector Daily Logger
**CLAUDE.md** · Zero-dependency Python + SQLite · SMB Sector: Coffee Shop

---

## Project overview

A full-stack daily logger for a coffee shop. Baristas use the POS page to tap items onto a ticket and place orders; the dashboard tracks revenue, top items, and category mix — filtered by any date or shown all-time.

Every order logged here persists across restarts. The end-of-day report (`GET /api/daily-report`) gives a manager a single clean summary they can print or export.

---

## Tech stack

| Layer     | Tech                                         |
|-----------|----------------------------------------------|
| Backend   | Python 3 stdlib — `http.server`, `sqlite3`   |
| Database  | SQLite (single file `coffee.db`)             |
| Frontend  | Vanilla JS SPA (`index.html`)                |
| Tests     | Python `unittest` + `urllib` (zero pip)      |
| Deps      | **None** — runs on any machine with Python 3 |

---

## Project structure

```
coffee-shop/
├── server.py          # HTTP server + all API handlers
├── index.html         # Single-page frontend (home / menu / order / dashboard)
├── test_api.py        # API test suite — run while server is up
├── coffee.db          # SQLite database (auto-created on first run)
├── CLAUDE.md          # This file
└── README.md          # Quick-start guide
```

---

## How to run

```bash
# 1 — start the server
cd coffee-shop
python server.py          # or python3 server.py

# 2 — open the app
# Visit http://localhost:8000 in your browser

# 3 — run tests (server must be running)
python test_api.py
```

---

## API reference

All endpoints return JSON. Dates are `YYYY-MM-DD` strings.

### `POST /api/orders`
Log a single order line.

**Request body**
```json
{
  "item":     "Flat White",
  "category": "Espresso",
  "qty":      2,
  "price":    4.50,
  "date":     "2024-11-15",   // optional — defaults to today
  "note":     "oat milk"      // optional
}
```

**Response** `201`
```json
{ "id": 42, "date": "2024-11-15", "item": "Flat White",
  "category": "Espresso", "qty": 2, "price": 4.50, "note": "oat milk" }
```

**Errors**
- `400` — missing `item`, `price <= 0`, or `qty < 1`

---

### `GET /api/orders?date=YYYY-MM-DD`
List orders. Omit `date` for all orders (latest 200).

**Response** `200` — array of order objects (same shape as POST response).

---

### `DELETE /api/orders/:id`
Delete one order by ID.

**Response** `200`
```json
{ "deleted": 42 }
```

---

### `GET /api/stats?date=YYYY-MM-DD`
Aggregated stats for the dashboard. Omit `date` for all-time.

**Response** `200`
```json
{
  "totals":      { "total_orders": 38, "total_items": 74, "revenue": 312.50 },
  "by_category": [ { "category": "Espresso", "qty": 40, "revenue": 185.00 }, ... ],
  "top_items":   [ { "item": "Flat White", "qty": 18, "revenue": 81.00 }, ... ],
  "daily":       [ { "date": "2024-11-15", "orders": 12, "revenue": 87.25 }, ... ]
}
```

> `daily` always returns the last 30 days regardless of date filter — it powers the chart.

---

### `GET /api/daily-report?date=YYYY-MM-DD`
End-of-day summary for one date (defaults to today).
Returns everything a manager needs to close out a shift.

**Response** `200`
```json
{
  "date":           "2024-11-15",
  "total_orders":   38,
  "total_items":    74,
  "revenue":        312.50,
  "avg_order":      8.22,
  "busiest_hour":   "09:00",
  "top_item":       { "item": "Flat White", "qty": 18, "revenue": 81.00 },
  "by_category":    [ { "category": "Espresso", "qty": 40, "revenue": 185.00 }, ... ],
  "orders":         [ ... ]
}
```

---

## Database schema

```sql
CREATE TABLE orders (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  date      TEXT    NOT NULL DEFAULT (date('now')),
  item      TEXT    NOT NULL,
  category  TEXT    NOT NULL DEFAULT 'Other',
  qty       INTEGER NOT NULL DEFAULT 1,
  price     REAL    NOT NULL,
  note      TEXT
);
```

---

## Test suite

`test_api.py` contains **8 tests** across 2 classes. Run it while the server is up:

```bash
python test_api.py
```

| Class              | Test                                   | What it checks                                 |
|--------------------|----------------------------------------|------------------------------------------------|
| `TestPostOrder`    | `test_creates_order_and_returns_full_record` | 201 response, all fields present          |
|                    | `test_rejects_missing_item`            | 400 when item name is missing                  |
|                    | `test_rejects_zero_price`              | 400 when price is 0                            |
| `TestGetStats`     | `test_stats_returns_expected_keys`     | All 4 top-level keys present                   |
|                    | `test_totals_revenue_is_correct`       | Revenue ≥ seeded $44.50                        |
|                    | `test_date_filter_scopes_totals`       | Filtered totals are non-null                   |
|                    | `test_by_category_contains_coffee`     | "Coffee" category appears in today's stats     |
| `TestDailyReport`  | `test_daily_report_keys`               | All required fields present in report          |
|                    | `test_daily_report_revenue_correct`    | Revenue matches expected seeded total          |

---

## Architecture decisions

**Why Python stdlib?** No `pip install` step — runs on any machine with Python 3, no virtualenv needed. Perfect for a demo or internship project with unknown environment.

**Why single `server.py`?** Keeps the project approachable. For production, split into `models.py`, `routes.py`, `db.py`.

**Why SQLite?** Zero config, single file, ACID compliant. Fine for a single-location coffee shop up to ~10k orders/day.

**Why no ORM?** Explicit SQL is easier to read and reason about for a project this size.

**`daily` chart always unfiltered** — the dashboard bar chart needs 30 days of data to render. Filtering by date scopes `totals`, `by_category`, and `top_items` but not `daily`.

---

## What to build next

- [ ] Authentication (staff PIN or session token)
- [ ] Inventory tracking (ingredient deductions per order)
- [ ] Multi-location support (`location_id` column)
- [ ] Export daily report as CSV
- [ ] Webhook / Slack notification at end-of-day
- [ ] Docker container for easy deployment
