"""
Stage 1 — Data Ingest
Loads transactions.csv into SQLite (transactions table).
Run: python load_csv.py
"""

import csv
import os
import sqlite3

DB_PATH  = os.path.join(os.path.expanduser("~"), "coffee.db")
CSV_PATH = os.path.join(os.path.dirname(__file__), "transactions.csv")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_transactions_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id          INTEGER PRIMARY KEY,
            date        TEXT    NOT NULL,
            item        TEXT    NOT NULL,
            amount      REAL    NOT NULL,
            customer_id TEXT    NOT NULL
        )
    """)
    conn.commit()
    print("[DB] transactions table ready")


def load_csv(conn):
    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        rows = [
            (int(r["id"]), r["date"], r["item"], float(r["amount"]), r["customer_id"])
            for r in reader
        ]

    # Clear existing data so re-runs are idempotent
    conn.execute("DELETE FROM transactions")
    conn.executemany(
        "INSERT INTO transactions (id, date, item, amount, customer_id) VALUES (?,?,?,?,?)",
        rows
    )
    conn.commit()
    return len(rows)


def print_summary(conn):
    total   = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    revenue = conn.execute("SELECT ROUND(SUM(amount),2) FROM transactions").fetchone()[0]
    uniq    = conn.execute("SELECT COUNT(DISTINCT customer_id) FROM transactions").fetchone()[0]
    first   = conn.execute("SELECT MIN(date) FROM transactions").fetchone()[0]
    last    = conn.execute("SELECT MAX(date) FROM transactions").fetchone()[0]

    print(f"\n  Rows loaded   : {total}")
    print(f"  Total revenue : ${revenue:,.2f}")
    print(f"  Unique customers: {uniq}")
    print(f"  Date range    : {first}  →  {last}")

    print("\n  Top 5 items by revenue:")
    rows = conn.execute("""
        SELECT item, COUNT(*) AS txns, ROUND(SUM(amount),2) AS revenue
        FROM transactions
        GROUP BY item ORDER BY revenue DESC LIMIT 5
    """).fetchall()
    for r in rows:
        print(f"    {r['item']:<25} {r['txns']} txns   ${r['revenue']}")


if __name__ == "__main__":
    print(f"[DB] Connecting to {DB_PATH}")
    with get_db() as conn:
        init_transactions_table(conn)
        n = load_csv(conn)
        print(f"[CSV] Loaded {n} rows from {CSV_PATH}")
        print_summary(conn)
    print("\n✅  Stage 1 complete — transactions loaded into SQLite")
