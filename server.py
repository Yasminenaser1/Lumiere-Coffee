"""
Coffee Shop App — Python stdlib only (no pip installs needed)
Run: python3 server.py
Then open: http://localhost:8000
"""

import json
import sqlite3
import os
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import date
from stats import revenue_by_day, top_items, repeat_customer_rate, average_ticket
from insights import get_insights
from agent import ask as agent_ask
from load_csv import init_transactions_table, load_csv as _load_csv, CSV_PATH

DB_PATH = os.path.join(os.path.expanduser("~"), "coffee.db")

# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                date      TEXT    NOT NULL DEFAULT (date('now')),
                item      TEXT    NOT NULL,
                category  TEXT    NOT NULL DEFAULT 'Other',
                qty       INTEGER NOT NULL DEFAULT 1,
                price     REAL    NOT NULL,
                note      TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_log (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                date      TEXT    NOT NULL DEFAULT (date('now')),
                sector    TEXT    NOT NULL,
                sales     REAL    NOT NULL,
                customers INTEGER NOT NULL
            )
        """)
        conn.commit()
    print(f"[DB] SQLite ready at {DB_PATH}")

    # Auto-seed transactions table from CSV if empty
    with get_db() as conn:
        init_transactions_table(conn)
        count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        if count == 0 and os.path.exists(CSV_PATH):
            n = _load_csv(conn)
            print(f"[CSV] Auto-loaded {n} transactions from {CSV_PATH}")

# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print(f"  {self.address_string()} — {fmt % args}")

    # ---- routing ----

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path
        qs     = parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self._serve_file("index.html", "text/html")
        elif path == "/api/orders":
            self._get_orders(qs)
        elif path == "/api/stats":
            self._get_stats(qs)
        elif path == "/api/summary":
            self._get_summary(qs)
        elif path == "/api/daily-report":
            self._get_daily_report(qs)
        elif path == "/api/log":
            self._get_log(qs)
        elif path == "/api/stats/revenue-by-day":
            try:
                self._json(revenue_by_day(int(qs.get("limit", [30])[0])))
            except Exception:
                self._json([])
        elif path == "/api/stats/top-items":
            try:
                self._json(top_items(int(qs.get("limit", [5])[0])))
            except Exception:
                self._json([])
        elif path == "/api/stats/repeat-customers":
            try:
                self._json(repeat_customer_rate())
            except Exception:
                self._json({"total_customers": 0, "repeat_customers": 0, "one_time_customers": 0, "repeat_rate_pct": 0})
        elif path == "/api/stats/average-ticket":
            try:
                self._json(average_ticket())
            except Exception:
                self._json({"total_transactions": 0, "total_revenue": 0, "avg_ticket": 0, "min_ticket": 0, "max_ticket": 0})
        elif path == "/api/insights":
            try:
                rev   = revenue_by_day(limit=7)
                items = top_items(limit=3)
                rc    = repeat_customer_rate()
                at    = average_ticket()
                top   = items[0] if items else {}
                top2  = items[1] if len(items) > 1 else {}
                best  = max(rev, key=lambda r: r["revenue"]) if rev else {}
                total_rev = at.get("total_revenue", 0) or 0
                avg       = at.get("avg_ticket", 0) or 0
                repeat    = rc.get("repeat_rate_pct", 0) or 0
                repeats   = rc.get("repeat_customers", 0) or 0
                total_c   = rc.get("total_customers", 0) or 0
                summary = (
                    f"Lumière Coffee is performing well. Total revenue across all transactions is "
                    f"${total_rev:,.2f} with an average ticket of ${avg:.2f}. "
                    + (f"Best day was {best['date']} with ${best['revenue']} in revenue. " if best else "")
                    + "\n\n"
                    + (f"Top seller: {top['item']} at ${top['revenue']} total revenue across {top['transactions']} transactions. " if top else "")
                    + (f"Second: {top2['item']} with ${top2['revenue']}. " if top2 else "")
                    + "\n\n"
                    + f"Customer loyalty is {'strong' if repeat >= 50 else 'building'}: {repeat}% of {total_c} customers "
                    + f"returned more than once ({repeats} repeat visitors). "
                    + "Consider a loyalty stamp card to boost retention, and a combo deal on your top item to raise the average ticket."
                )
            except Exception:
                summary = ("Lumière Coffee is running smoothly with strong sales and loyal customers. "
                           "Focus on promoting top-selling items and introducing a loyalty program "
                           "to keep customers coming back.")
            self._json({"insights": summary, "model": "local"})
        elif path == "/api/ask":
            question = qs.get("q", [""])[0].strip()
            if not question:
                self._json({"error": "Missing ?q= parameter"}, 400)
            else:
                try:
                    at    = average_ticket()
                    items = top_items(limit=3)
                    rc    = repeat_customer_rate()
                    rev   = revenue_by_day(limit=7)
                    top   = items[0] if items else {}
                    best  = max(rev, key=lambda r: r["revenue"]) if rev else {}
                    q     = question.lower()
                    if any(w in q for w in ["best", "top", "popular", "most"]):
                        ans = (f"Your top item is {top.get('item','N/A')} with "
                               f"${top.get('revenue',0)} in revenue across "
                               f"{top.get('transactions',0)} transactions.")
                    elif any(w in q for w in ["revenue", "sales", "money", "earn"]):
                        ans = (f"Total revenue is ${at.get('total_revenue',0):,.2f} "
                               f"across {at.get('total_transactions',0)} transactions."
                               + (f" Best day: {best['date']} with ${best['revenue']}." if best else ""))
                    elif any(w in q for w in ["customer", "loyal", "repeat", "return"]):
                        ans = (f"{rc.get('repeat_rate_pct',0)}% of your "
                               f"{rc.get('total_customers',0)} customers returned more than once.")
                    elif any(w in q for w in ["average", "ticket", "avg"]):
                        ans = (f"Average ticket is ${at.get('avg_ticket',0):.2f}. "
                               f"Min: ${at.get('min_ticket',0)}, Max: ${at.get('max_ticket',0)}.")
                    else:
                        ans = (f"Total revenue: ${at.get('total_revenue',0):,.2f} | "
                               f"Avg ticket: ${at.get('avg_ticket',0):.2f} | "
                               f"Top item: {top.get('item','N/A')} | "
                               f"Repeat rate: {rc.get('repeat_rate_pct',0)}%")
                except Exception:
                    ans = "Stats are loading — please try again in a moment."
                self._json({"question": question, "answer": ans, "tools_called": [], "model": "local"})
        else:
            self._json({"error": "Not found"}, 404)

    def do_POST(self):
        if self.path == "/api/orders":
            self._post_order()
        elif self.path == "/api/log":
            self._post_log()
        else:
            self._json({"error": "Not found"}, 404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        parts = parsed.path.split("/")
        if len(parts) == 4 and parts[1] == "api" and parts[2] == "orders":
            try:
                order_id = int(parts[3])
                self._delete_order(order_id)
            except ValueError:
                self._json({"error": "Invalid ID"}, 400)
        else:
            self._json({"error": "Not found"}, 404)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    # ---- handlers ----

    def _get_orders(self, qs):
        day = qs.get("date", [None])[0]
        with get_db() as conn:
            if day:
                rows = conn.execute(
                    "SELECT * FROM orders WHERE date = ? ORDER BY id DESC", (day,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM orders ORDER BY id DESC LIMIT 200"
                ).fetchall()
        self._json([dict(r) for r in rows])

    def _get_stats(self, qs):
        day = qs.get("date", [None])[0]
        with get_db() as conn:
            if day:
                where = "WHERE date = ?"
                params = (day,)
            else:
                where, params = "", ()

            totals = conn.execute(f"""
                SELECT
                    COUNT(*)        AS total_orders,
                    SUM(qty)        AS total_items,
                    ROUND(SUM(price * qty), 2) AS revenue
                FROM orders {where}
            """, params).fetchone()

            by_category = conn.execute(f"""
                SELECT category,
                       SUM(qty) AS qty,
                       ROUND(SUM(price * qty), 2) AS revenue
                FROM orders {where}
                GROUP BY category
                ORDER BY revenue DESC
            """, params).fetchall()

            top_items = conn.execute(f"""
                SELECT item, SUM(qty) AS qty,
                       ROUND(SUM(price * qty), 2) AS revenue
                FROM orders {where}
                GROUP BY item
                ORDER BY qty DESC
                LIMIT 5
            """, params).fetchall()

            daily = conn.execute("""
                SELECT date,
                       COUNT(*) AS orders,
                       ROUND(SUM(price * qty), 2) AS revenue
                FROM orders
                GROUP BY date
                ORDER BY date DESC
                LIMIT 30
            """).fetchall()

        self._json({
            "totals":      dict(totals) if totals else {},
            "by_category": [dict(r) for r in by_category],
            "top_items":   [dict(r) for r in top_items],
            "daily":       [dict(r) for r in daily],
        })

    def _get_daily_report(self, qs):
        """End-of-day summary for a single date — defaults to today."""
        day = qs.get("date", [None])[0] or str(date.today())

        with get_db() as conn:
            totals = conn.execute("""
                SELECT COUNT(*) AS total_orders,
                       SUM(qty) AS total_items,
                       ROUND(SUM(price * qty), 2) AS revenue
                FROM orders WHERE date = ?
            """, (day,)).fetchone()

            by_category = conn.execute("""
                SELECT category,
                       SUM(qty) AS qty,
                       ROUND(SUM(price * qty), 2) AS revenue
                FROM orders WHERE date = ?
                GROUP BY category ORDER BY revenue DESC
            """, (day,)).fetchall()

            top_item = conn.execute("""
                SELECT item, SUM(qty) AS qty,
                       ROUND(SUM(price * qty), 2) AS revenue
                FROM orders WHERE date = ?
                GROUP BY item ORDER BY qty DESC LIMIT 1
            """, (day,)).fetchone()

            orders = conn.execute("""
                SELECT * FROM orders WHERE date = ? ORDER BY id
            """, (day,)).fetchall()

        t = dict(totals) if totals else {}
        revenue  = t.get("revenue") or 0
        n_orders = t.get("total_orders") or 0
        avg_order = round(revenue / n_orders, 2) if n_orders else 0

        self._json({
            "date":         day,
            "total_orders": n_orders,
            "total_items":  t.get("total_items") or 0,
            "revenue":      revenue,
            "avg_order":    avg_order,
            "top_item":     dict(top_item) if top_item else None,
            "by_category":  [dict(r) for r in by_category],
            "orders":       [dict(r) for r in orders],
        })

    # ---- daily_log handlers ----

    def _post_log(self):
        """POST /api/log — add one row to daily_log."""
        length = int(self.headers.get("Content-Length", 0))
        body   = json.loads(self.rfile.read(length) or b"{}")

        sector    = str(body.get("sector", "")).strip()
        sales     = float(body.get("sales", -1))
        customers = int(body.get("customers", -1))
        day       = body.get("date") or str(date.today())

        if not sector or sales < 0 or customers < 0:
            self._json({"error": "sector, sales >= 0, and customers >= 0 required"}, 400)
            return

        with get_db() as conn:
            cur = conn.execute(
                "INSERT INTO daily_log (date, sector, sales, customers) VALUES (?,?,?,?)",
                (day, sector, sales, customers)
            )
            conn.commit()
            row = conn.execute("SELECT * FROM daily_log WHERE id = ?", (cur.lastrowid,)).fetchone()

        self._json(dict(row), 201)

    def _get_log(self, qs):
        """GET /api/log — list daily_log entries, optional ?date= filter."""
        day = qs.get("date", [None])[0]
        with get_db() as conn:
            if day:
                rows = conn.execute(
                    "SELECT * FROM daily_log WHERE date = ? ORDER BY id DESC", (day,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM daily_log ORDER BY id DESC LIMIT 200"
                ).fetchall()
        self._json([dict(r) for r in rows])

    def _get_summary(self, qs):
        """GET /api/summary — totals + series from daily_log."""
        day = qs.get("date", [None])[0]
        with get_db() as conn:
            if day:
                where, params = "WHERE date = ?", (day,)
            else:
                where, params = "", ()

            totals = conn.execute(f"""
                SELECT
                    COUNT(*)              AS total_entries,
                    ROUND(SUM(sales), 2)  AS total_sales,
                    SUM(customers)        AS total_customers
                FROM daily_log {where}
            """, params).fetchone()

            by_sector = conn.execute(f"""
                SELECT sector,
                       ROUND(SUM(sales), 2) AS sales,
                       SUM(customers)       AS customers
                FROM daily_log {where}
                GROUP BY sector
                ORDER BY sales DESC
            """, params).fetchall()

            series = conn.execute("""
                SELECT date,
                       ROUND(SUM(sales), 2) AS sales,
                       SUM(customers)       AS customers
                FROM daily_log
                GROUP BY date
                ORDER BY date DESC
                LIMIT 30
            """).fetchall()

        self._json({
            "totals":    dict(totals) if totals else {},
            "by_sector": [dict(r) for r in by_sector],
            "series":    [dict(r) for r in series],
        })

    # ---- orders handlers ----

    def _post_order(self):
        length = int(self.headers.get("Content-Length", 0))
        body   = json.loads(self.rfile.read(length) or b"{}")

        item     = str(body.get("item", "")).strip()
        category = str(body.get("category", "Other")).strip()
        qty      = int(body.get("qty", 1))
        price    = float(body.get("price", 0))
        note     = str(body.get("note", "")).strip()
        day      = body.get("date") or str(date.today())

        if not item or price <= 0 or qty < 1:
            self._json({"error": "item, price > 0 and qty >= 1 required"}, 400)
            return

        with get_db() as conn:
            cur = conn.execute(
                "INSERT INTO orders (date, item, category, qty, price, note) VALUES (?,?,?,?,?,?)",
                (day, item, category, qty, price, note)
            )
            conn.commit()
            row = conn.execute("SELECT * FROM orders WHERE id = ?", (cur.lastrowid,)).fetchone()

        self._json(dict(row), 201)

    def _delete_order(self, order_id):
        with get_db() as conn:
            conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
            conn.commit()
        self._json({"deleted": order_id})

    # ---- helpers ----

    def _serve_file(self, filename, content_type):
        filepath = os.path.join(os.path.dirname(__file__), filename)
        try:
            with open(filepath, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", len(data))
            self._cors_headers()
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self._json({"error": f"{filename} not found"}, 404)

    def _json(self, data, status=200):
        body = json.dumps(data, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Background job — snapshot daily report every hour
# ---------------------------------------------------------------------------

SNAPSHOT_PATH = os.path.join(os.path.dirname(__file__), "daily_snapshot.json")

def _snapshot_job():
    """Background thread: saves a daily report snapshot to disk every hour."""
    while True:
        try:
            today = date.today().isoformat()
            with get_db() as conn:
                rows = conn.execute(
                    "SELECT * FROM orders WHERE date = ? ORDER BY id DESC", (today,)
                ).fetchall()
                orders = [dict(r) for r in rows]
                total_orders  = len(orders)
                total_items   = sum(o["qty"] for o in orders)
                revenue       = round(sum(o["price"] * o["qty"] for o in orders), 2)
                avg_order     = round(revenue / total_orders, 2) if total_orders else 0

            snapshot = {
                "generated_at":  time.strftime("%Y-%m-%dT%H:%M:%S"),
                "date":          today,
                "total_orders":  total_orders,
                "total_items":   total_items,
                "revenue":       revenue,
                "avg_order":     avg_order,
            }
            with open(SNAPSHOT_PATH, "w") as f:
                json.dump(snapshot, f, indent=2)
            print(f"[BG] Snapshot saved → {today}  revenue=${revenue}  orders={total_orders}")
        except Exception as e:
            print(f"[BG] Snapshot error: {e}")
        time.sleep(3600)  # run every hour


if __name__ == "__main__":
    init_db()
    from agent import GROQ_API_KEY as _key
    print(f"[AI] Groq key loaded: {_key[:12]}..." if _key else "[AI] ⚠️  No GROQ_API_KEY found")

    # Start background job thread (daemon so it exits when server stops)
    bg = threading.Thread(target=_snapshot_job, daemon=True)
    bg.start()
    print("[BG] Daily snapshot job started (runs every hour)")

    PORT = int(os.environ.get("PORT", 8000))   # Render sets PORT automatically
    server = HTTPServer(("", PORT), Handler)
    print(f"☕  Coffee Shop running → http://localhost:{PORT}")
    server.serve_forever()


