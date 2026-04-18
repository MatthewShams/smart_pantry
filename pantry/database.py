"""SQLite persistence for pantry state."""

import sqlite3
from datetime import datetime, timedelta
from config import DB_PATH


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS ingredients (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT    NOT NULL,
            category     TEXT,
            quantity     REAL,
            unit         TEXT,
            shelf_slot   INTEGER,          -- maps directly to LED index
            expiry_date  TEXT,             -- ISO-8601 YYYY-MM-DD
            last_seen    TEXT,             -- ISO-8601 timestamp of last scan
            notes        TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS scan_history (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp     TEXT NOT NULL,
            raw_response  TEXT,
            items_detected INTEGER
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS saved_recipes (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            ingredients  TEXT,             -- JSON array of ingredient names
            instructions TEXT,
            prep_time    INTEGER,
            tags         TEXT              -- comma-separated
        )
    """)

    conn.commit()
    conn.close()


# ── CRUD helpers ──────────────────────────────────────────────────────────

def upsert_ingredient(name, category=None, quantity=None, unit=None,
                      shelf_slot=None, expiry_date=None, notes=None):
    """Insert or update an ingredient by name."""
    conn = get_db()
    now = datetime.now().isoformat()
    existing = conn.execute(
        "SELECT id FROM ingredients WHERE LOWER(name) = LOWER(?)", (name,)
    ).fetchone()

    if existing:
        conn.execute(
            """UPDATE ingredients
               SET category=?, quantity=?, unit=?, shelf_slot=?,
                   expiry_date=?, last_seen=?, notes=?
               WHERE id=?""",
            (category, quantity, unit, shelf_slot, expiry_date, now, notes, existing["id"])
        )
    else:
        conn.execute(
            """INSERT INTO ingredients
               (name, category, quantity, unit, shelf_slot, expiry_date, last_seen, notes)
               VALUES (?,?,?,?,?,?,?,?)""",
            (name, category, quantity, unit, shelf_slot, expiry_date, now, notes)
        )
    conn.commit()
    conn.close()


def get_all_ingredients() -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM ingredients ORDER BY shelf_slot NULLS LAST, name"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_ingredient_by_name(name: str) -> dict | None:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM ingredients WHERE LOWER(name)=LOWER(?)", (name,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_ingredient(ingredient_id: int):
    conn = get_db()
    conn.execute("DELETE FROM ingredients WHERE id=?", (ingredient_id,))
    conn.commit()
    conn.close()


def get_expiring_soon(days: int = 7) -> list[dict]:
    today  = datetime.now().date().isoformat()
    cutoff = (datetime.now() + timedelta(days=days)).date().isoformat()
    conn   = get_db()
    rows   = conn.execute(
        """SELECT * FROM ingredients
           WHERE expiry_date IS NOT NULL
             AND expiry_date >= ? AND expiry_date <= ?""",
        (today, cutoff)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_expired() -> list[dict]:
    today = datetime.now().date().isoformat()
    conn  = get_db()
    rows  = conn.execute(
        "SELECT * FROM ingredients WHERE expiry_date IS NOT NULL AND expiry_date < ?",
        (today,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def log_scan(raw_response: str, items_detected: int):
    conn = get_db()
    conn.execute(
        "INSERT INTO scan_history (timestamp, raw_response, items_detected) VALUES (?,?,?)",
        (datetime.now().isoformat(), raw_response, items_detected)
    )
    conn.commit()
    conn.close()


def save_recipe(name, ingredients: list, instructions: str, prep_time: int, tags: list):
    import json
    conn = get_db()
    conn.execute(
        """INSERT INTO saved_recipes (name, ingredients, instructions, prep_time, tags)
           VALUES (?,?,?,?,?)""",
        (name, json.dumps(ingredients), instructions, prep_time, ",".join(tags))
    )
    conn.commit()
    conn.close()


def get_saved_recipes() -> list[dict]:
    import json
    conn  = get_db()
    rows  = conn.execute("SELECT * FROM saved_recipes ORDER BY name").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["ingredients"] = json.loads(d["ingredients"] or "[]")
        d["tags"]        = d["tags"].split(",") if d["tags"] else []
        result.append(d)
    return result
