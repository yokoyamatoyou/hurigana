from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Optional, Tuple


def init_db(path: str | Path = "furigana.db") -> sqlite3.Connection:
    """Initialize and return a SQLite connection."""
    conn = sqlite3.connect(path)
    with conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS readings ("
            "name TEXT NOT NULL,"
            "reading TEXT NOT NULL,"
            "confidence INTEGER NOT NULL,"
            "reason TEXT NOT NULL,"
            "PRIMARY KEY(name, reading)"
            ")"
        )
    return conn


def get_reading(
    name: str, reading: str, conn: sqlite3.Connection
) -> Optional[Tuple[int, str]]:
    """Retrieve cached confidence and reason for ``name`` and ``reading``."""
    cur = conn.execute(
        "SELECT confidence, reason FROM readings WHERE name=? AND reading=?",
        (name, reading),
    )
    row = cur.fetchone()
    if row:
        return int(row[0]), row[1]
    return None


def save_reading(
    name: str,
    reading: str,
    confidence: int,
    reason: str,
    conn: sqlite3.Connection,
) -> None:
    """Save result to the database."""
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO readings (name, reading, confidence, reason) "
            "VALUES (?, ?, ?, ?)",
            (name, reading, confidence, reason),
        )

