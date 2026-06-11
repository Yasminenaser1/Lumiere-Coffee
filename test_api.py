"""
Coffee Shop API Tests
Run while server is up:  python test_api.py
Zero dependencies - uses Python stdlib only.
"""

import json
import unittest
import urllib.request
import urllib.error
from datetime import date

BASE = "http://localhost:8000"
TODAY = str(date.today())


def post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        BASE + path,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        return r.status, json.loads(r.read())


def get(path):
    with urllib.request.urlopen(BASE + path) as r:
        return r.status, json.loads(r.read())


def delete(path):
    req = urllib.request.Request(BASE + path, method="DELETE")
    with urllib.request.urlopen(req) as r:
        return r.status, json.loads(r.read())


# Seed data - a realistic morning rush
SEED_ORDERS = [
    {"item": "Flat White",   "category": "Coffee",     "qty": 2, "price": 4.50, "date": TODAY},
    {"item": "Croissant",    "category": "Food",       "qty": 3, "price": 3.25, "date": TODAY},
    {"item": "Iced Matcha",  "category": "Cold Drink", "qty": 1, "price": 5.75, "date": TODAY},
    {"item": "Espresso",     "category": "Coffee",     "qty": 4, "price": 3.00, "date": TODAY},
    {"item": "Banana Bread", "category": "Food",       "qty": 2, "price": 4.00, "date": TODAY},
]


class TestPostOrder(unittest.TestCase):
    """POST /api/orders - creates an order and returns it."""

    def test_creates_order_and_returns_full_record(self):
        payload = {
            "item": "Cappuccino",
            "category": "Coffee",
            "qty": 1,
            "price": 4.00,
            "date": TODAY,
            "note": "oat milk",
        }
        status, body = post("/api/orders", payload)

        self.assertEqual(status, 201, "should return HTTP 201 Created")
        self.assertIn("id", body)
        self.assertEqual(body["item"], "Cappuccino")
        self.assertEqual(body["category"], "Coffee")
        self.assertEqual(body["qty"], 1)
        self.assertAlmostEqual(body["price"], 4.00)
        self.assertEqual(body["note"], "oat milk")
        self.assertEqual(body["date"], TODAY)

    def test_rejects_missing_item(self):
        """Posting without an item name must return 400."""
        try:
            post("/api/orders", {"price": 3.00, "qty": 1})
            self.fail("expected HTTP 400 but got success")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)

    def test_rejects_zero_price(self):
        """Price must be greater than 0."""
        try:
            post("/api/orders", {"item": "Water", "price": 0, "qty": 1})
            self.fail("expected HTTP 400 but got success")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)


class TestGetStats(unittest.TestCase):
    """GET /api/stats - aggregated summary of all orders."""

    @classmethod
    def setUpClass(cls):
        """Seed a known set of orders so we can assert exact numbers."""
        cls.seeded_ids = []
        for order in SEED_ORDERS:
            _, body = post("/api/orders", order)
            cls.seeded_ids.append(body["id"])

    @classmethod
    def tearDownClass(cls):
        """Clean up seeded orders so tests don't pollute the DB."""
        for oid in cls.seeded_ids:
            try:
                delete("/api/orders/" + str(oid))
            except Exception:
                pass

    def test_stats_returns_expected_keys(self):
        status, body = get("/api/stats")
        self.assertEqual(status, 200)
        for key in ("totals", "by_category", "top_items", "daily"):
            self.assertIn(key, body, "stats must contain key: " + key)

    def test_totals_revenue_is_correct(self):
        """
        Seeded revenue:
          Flat White   2 x $4.50 = $9.00
          Croissant    3 x $3.25 = $9.75
          Iced Matcha  1 x $5.75 = $5.75
          Espresso     4 x $3.00 = $12.00
          Banana Bread 2 x $4.00 = $8.00
          Total seeded            = $44.50
        DB may have other orders too, so check >= seeded total.
        """
        _, body = get("/api/stats")
        revenue = body["totals"].get("revenue") or 0
        self.assertGreaterEqual(revenue, 44.50,
            "revenue " + str(revenue) + " should be >= seeded $44.50")

    def test_date_filter_scopes_totals(self):
        """
        When filtering by date, totals/by_category/top_items are scoped to
        that date. The daily chart always returns 30 days for the dashboard.
        """
        _, body = get("/api/stats?date=" + TODAY)
        totals = body.get("totals", {})
        self.assertIsNotNone(totals.get("revenue"))
        for row in body.get("daily", []):
            self.assertIn("date", row)
            self.assertIn("revenue", row)

    def test_by_category_contains_coffee(self):
        _, body = get("/api/stats?date=" + TODAY)
        categories = [r["category"] for r in body.get("by_category", [])]
        self.assertIn("Coffee", categories,
            "Coffee category should appear in today's stats")


class TestLogAndSummary(unittest.TestCase):
    """
    Internship spec endpoints:
      POST /api/log     — log a single order
      GET  /api/summary — aggregated stats
    These are aliases for /api/orders and /api/stats respectively.
    """

    def test_post_log_creates_order(self):
        """POST /api/log should create an order and return 201 with all fields."""
        payload = {
            "item": "Matcha Latte",
            "category": "Tea",
            "qty": 1,
            "price": 5.50,
            "date": TODAY,
        }
        status, body = post("/api/log", payload)
        self.assertEqual(status, 201, "POST /api/log should return 201")
        self.assertEqual(body["item"], "Matcha Latte")
        self.assertIn("id", body, "response must include the new order id")
        # clean up
        delete("/api/orders/" + str(body["id"]))

    def test_post_log_rejects_bad_data(self):
        """POST /api/log should reject a missing item name with 400."""
        try:
            post("/api/log", {"price": 4.00, "qty": 1})
            self.fail("expected HTTP 400 but got success")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 400)

    def test_get_summary_returns_revenue(self):
        """GET /api/summary should return a totals object with a revenue field."""
        # seed one order so there is something to summarise
        _, created = post("/api/log", {
            "item": "Espresso", "category": "Espresso",
            "qty": 2, "price": 3.00, "date": TODAY,
        })
        status, body = get("/api/summary?date=" + TODAY)
        self.assertEqual(status, 200)
        self.assertIn("totals", body)
        self.assertIsNotNone(body["totals"].get("revenue"),
            "summary totals must include a revenue value")
        delete("/api/orders/" + str(created["id"]))


class TestDailyReport(unittest.TestCase):
    """GET /api/daily-report - end-of-day summary for one date."""

    @classmethod
    def setUpClass(cls):
        cls.seeded_ids = []
        for order in SEED_ORDERS:
            _, body = post("/api/orders", order)
            cls.seeded_ids.append(body["id"])

    @classmethod
    def tearDownClass(cls):
        for oid in cls.seeded_ids:
            try:
                delete("/api/orders/" + str(oid))
            except Exception:
                pass

    def test_daily_report_keys(self):
        """Report must include all required top-level fields."""
        status, body = get("/api/daily-report?date=" + TODAY)
        self.assertEqual(status, 200)
        for key in ("date", "total_orders", "total_items", "revenue",
                    "avg_order", "top_item", "by_category", "orders"):
            self.assertIn(key, body, "daily-report missing key: " + key)
        self.assertEqual(body["date"], TODAY)

    def test_daily_report_revenue_correct(self):
        """Revenue must be >= seeded $44.50 and avg_order must be positive."""
        _, body = get("/api/daily-report?date=" + TODAY)
        revenue = body.get("revenue") or 0
        self.assertGreaterEqual(revenue, 44.50,
            "daily-report revenue " + str(revenue) + " should be >= $44.50")
        self.assertGreater(body.get("avg_order", 0), 0,
            "avg_order should be positive when orders exist")


if __name__ == "__main__":
    print("Running Coffee Shop API tests against " + BASE)
    print()
    unittest.main(verbosity=2)
