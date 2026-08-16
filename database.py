"""
database.py
Small SQLite helper layer for the chat app.
Stores rooms and messages (both room messages and DMs, distinguished by
the `channel` value: room names are plain, e.g. "general"; DMs are
"dm:<nickA>:<nickB>" with nicknames sorted alphabetically).
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "chat.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            name TEXT PRIMARY KEY,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel TEXT NOT NULL,
            sender TEXT NOT NULL,
            text TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_channel ON messages(channel)")

    # Always make sure the default room exists.
    cur.execute(
        "INSERT OR IGNORE INTO rooms (name, created_at) VALUES (?, ?)",
        ("general", datetime.utcnow().isoformat()),
    )

    conn.commit()
    conn.close()


def dm_channel_name(nick_a: str, nick_b: str) -> str:
    """Deterministic channel name for a DM between two nicknames."""
    a, b = sorted([nick_a.lower(), nick_b.lower()])
    return f"dm:{a}:{b}"


def create_room_if_missing(room_name: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO rooms (name, created_at) VALUES (?, ?)",
        (room_name, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def list_rooms():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM rooms ORDER BY name ASC")
    rows = cur.fetchall()
    conn.close()
    return [r["name"] for r in rows]


def save_message(channel: str, sender: str, text: str) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    timestamp = datetime.utcnow().isoformat()
    cur.execute(
        "INSERT INTO messages (channel, sender, text, timestamp) VALUES (?, ?, ?, ?)",
        (channel, sender, text, timestamp),
    )
    conn.commit()
    conn.close()
    return {"channel": channel, "sender": sender, "text": text, "timestamp": timestamp}


def get_history(channel: str, limit: int = 100):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT sender, text, timestamp FROM messages WHERE channel = ? "
        "ORDER BY id DESC LIMIT ?",
        (channel, limit),
    )
    rows = cur.fetchall()
    conn.close()
    # Return in chronological order.
    return [dict(r) for r in reversed(rows)]
