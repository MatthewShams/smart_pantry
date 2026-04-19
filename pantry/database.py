import sqlite3
from datetime import datetime
from config import DB_PATH

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the schema seen in your pantry.db file."""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ingredients (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                name         TEXT NOT NULL,
                category     TEXT,
                quantity     REAL,
                unit         TEXT,
                shelf_slot   INTEGER,
                expiry_date  TEXT,
                last_seen    TEXT,
                notes        TEXT
            )
        """)
        # Also need scan_history as per your DB schema
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scan_history (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp     TEXT NOT NULL,
                raw_response  TEXT,
                items_detected INTEGER
            )
        """)
        conn.commit()

def upsert_ingredient(name, category=None, quantity=None, unit=None, shelf_slot=None, expiry_date=None, notes=None):
    with get_db() as conn:
        now  = datetime.now().isoformat()
        name = name.lower().strip()

        if shelf_slot is not None:
            existing = conn.execute(
                "SELECT id FROM ingredients WHERE shelf_slot = ?", (shelf_slot,)
            ).fetchone()
        else:
            existing = conn.execute(
                "SELECT id FROM ingredients WHERE name = ? AND shelf_slot IS NULL", (name,)
            ).fetchone()

        if existing:
            conn.execute(
                """UPDATE ingredients
                   SET name=?, category=?, quantity=?, unit=?, expiry_date=?, last_seen=?, notes=?
                   WHERE id=?""",
                (name, category, quantity, unit, expiry_date, now, notes, existing["id"]),
            )
        else:
            conn.execute(
                """INSERT INTO ingredients
                       (name, category, quantity, unit, shelf_slot, expiry_date, last_seen, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, category, quantity, unit, shelf_slot, expiry_date, now, notes),
            )
        conn.commit()

def get_all_ingredients():
    with get_db() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM ingredients").fetchall()]

def log_scan(raw_response, count):
    with get_db() as conn:
        conn.execute("INSERT INTO scan_history (timestamp, raw_response, items_detected) VALUES (?, ?, ?)",
                    (datetime.now().isoformat(), raw_response, count))
        conn.commit()

# Adding these to support your app.py routes
def get_expired():
    with get_db() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM ingredients WHERE expiry_date < date('now')").fetchall()]

def get_expiring_soon(days=7):
    with get_db() as conn:
        return [dict(row) for row in conn.execute(f"SELECT * FROM ingredients WHERE expiry_date >= date('now') AND expiry_date <= date('now', '+{days} days')").fetchall()]

def delete_ingredient(ing_id):
    with get_db() as conn:
        conn.execute("DELETE FROM ingredients WHERE id = ?", (ing_id,))
        conn.commit()
