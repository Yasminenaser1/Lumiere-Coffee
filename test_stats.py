"""
Stage 6 — Tests for the Stage 2 stats pipeline.
Uses a temporary in-memory SQLite DB seeded with known data so tests are
deterministic and don't depend on the user's coffee.db.

Run: python -m pytest test_stats.py -v
  or: python test_stats.py
"""

import sqlite3
import unittest
import os
import tempfile
import stats  # the module we're testing


# ---------------------------------------------------------------------------
# Known seed data — fixed so we can assert exact values
# ---------------------------------------------------------------------------

SEED_ROWS = [
    # (date, item, amount, customer_id)
    ("2026-06-01", "Latte",      5.00, "c001"),
    ("2026-06-01", "Croissant",  3.25, "c002"),
    ("2026-06-01", "Cold Brew",  5.00, "c001"),   # c001 returns → repeat
    ("2026-06-02", "Latte",      5.10, "c003"),
    ("2026-06-02", "Espresso",   3.00, "c004"),
    ("2026-06-03", "Granola Bowl", 6.50, "c002"), # c002 returns → repeat
    ("2026-06-03", "Latte",      4.90, "c005"),   # one-time
]
# revenue totals:
# Latte:       5.00 + 5.10 + 4.90 = 15.00  (3 txns, avg 5.00)
# Cold Brew:   5.00                          (1 txn)
# Croissant:   3.25                          (1 txn)
# Espresso:    3.00                          (1 txn)
# Granola Bowl:6.50                          (1 txn)
# Total: 32.75  /  7 transactions
# Customers: c001, c002, c003, c004, c005 = 5 total
# Repeats: c001 (2 visits), c002 (2 visits) = 2 repeats → 40% rate


class TestStats(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Create a temp DB, seed it, and point stats.DB_PATH at it."""
        fd, cls.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        conn = sqlite3.connect(cls.db_path)
        conn.execute("""
            CREATE TABLE transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT NOT NULL,
                item        TEXT NOT NULL,
                amount      REAL NOT NULL,
                customer_id TEXT NOT NULL
            )
        """)
        conn.executemany(
            "INSERT INTO transactions (date, item, amount, customer_id) VALUES (?,?,?,?)",
            SEED_ROWS
        )
        conn.commit()
        conn.close()

        # Redirect stats module to our temp DB
        cls._original_path = stats.DB_PATH
        stats.DB_PATH = cls.db_path

    @classmethod
    def tearDownClass(cls):
        stats.DB_PATH = cls._original_path
        os.unlink(cls.db_path)

    # ------------------------------------------------------------------ #

    def test_revenue_by_day_returns_list(self):
        rows = stats.revenue_by_day()
        self.assertIsInstance(rows, list)

    def test_revenue_by_day_structure(self):
        rows = stats.revenue_by_day()
        for r in rows:
            self.assertIn("date", r)
            self.assertIn("transactions", r)
            self.assertIn("revenue", r)

    def test_revenue_by_day_correct_values(self):
        rows = stats.revenue_by_day()
        # 3 distinct dates in seed data
        self.assertEqual(len(rows), 3)

        # Most recent date first
        by_date = {r["date"]: r for r in rows}
        self.assertAlmostEqual(by_date["2026-06-01"]["revenue"], 13.25, places=2)
        self.assertAlmostEqual(by_date["2026-06-02"]["revenue"],  8.10, places=2)
        self.assertAlmostEqual(by_date["2026-06-03"]["revenue"], 11.40, places=2)

    def test_revenue_by_day_limit(self):
        rows = stats.revenue_by_day(limit=1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["date"], "2026-06-03")   # most recent

    # ------------------------------------------------------------------ #

    def test_top_items_returns_list(self):
        items = stats.top_items()
        self.assertIsInstance(items, list)

    def test_top_items_structure(self):
        items = stats.top_items()
        for item in items:
            self.assertIn("item", item)
            self.assertIn("revenue", item)
            self.assertIn("transactions", item)
            self.assertIn("avg_price", item)

    def test_top_items_latte_is_first(self):
        items = stats.top_items(limit=5)
        # Latte has highest revenue ($15.00)
        self.assertEqual(items[0]["item"], "Latte")
        self.assertAlmostEqual(items[0]["revenue"], 15.00, places=2)
        self.assertEqual(items[0]["transactions"], 3)

    # ------------------------------------------------------------------ #

    def test_repeat_customer_rate_structure(self):
        rc = stats.repeat_customer_rate()
        for key in ("total_customers", "repeat_customers", "one_time_customers", "repeat_rate_pct"):
            self.assertIn(key, rc)

    def test_repeat_customer_rate_correct_counts(self):
        rc = stats.repeat_customer_rate()
        self.assertEqual(rc["total_customers"],   5)
        self.assertEqual(rc["repeat_customers"],  2)   # c001, c002
        self.assertEqual(rc["one_time_customers"], 3)  # c003, c004, c005
        self.assertAlmostEqual(rc["repeat_rate_pct"], 40.0, places=1)

    # ------------------------------------------------------------------ #

    def test_average_ticket_structure(self):
        at = stats.average_ticket()
        for key in ("total_transactions", "total_revenue", "avg_ticket", "min_ticket", "max_ticket"):
            self.assertIn(key, at)

    def test_average_ticket_values(self):
        at = stats.average_ticket()
        self.assertEqual(at["total_transactions"], 7)
        self.assertAlmostEqual(at["total_revenue"], 32.75, places=2)
        self.assertAlmostEqual(at["avg_ticket"],    round(32.75 / 7, 2), places=2)
        self.assertAlmostEqual(at["min_ticket"], 3.00, places=2)
        self.assertAlmostEqual(at["max_ticket"], 6.50, places=2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
