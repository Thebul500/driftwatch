"""SQLite storage for snapshots.

Stores snapshots as JSON blobs in ``~/.driftwatch/driftwatch.db``.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DB_DIR = Path.home() / ".driftwatch"
DB_PATH = DB_DIR / "driftwatch.db"

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    data TEXT NOT NULL,
    is_baseline INTEGER NOT NULL DEFAULT 0
)
"""


def _get_conn(db_path: Path | None = None) -> sqlite3.Connection:
    """Get a connection to the SQLite database, creating it if needed."""
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute(_CREATE_TABLE)
    conn.commit()
    return conn


def save_snapshot(
    data: dict[str, Any],
    name: str | None = None,
    is_baseline: bool = False,
    db_path: Path | None = None,
) -> int:
    """Save a snapshot and return its ID."""
    conn = _get_conn(db_path)
    try:
        ts = datetime.now(UTC).isoformat()
        if name is None:
            name = f"snapshot-{ts[:19].replace(':', '-')}"
        cursor = conn.execute(
            "INSERT INTO snapshots (name, timestamp, data, is_baseline) VALUES (?, ?, ?, ?)",
            (name, ts, json.dumps(data, sort_keys=True), int(is_baseline)),
        )
        conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]
    finally:
        conn.close()


def get_snapshot(snapshot_id: int, db_path: Path | None = None) -> dict | None:
    """Get a snapshot by ID. Returns None if not found."""
    conn = _get_conn(db_path)
    try:
        row = conn.execute("SELECT * FROM snapshots WHERE id = ?", (snapshot_id,)).fetchone()
        if row is None:
            return None
        return _row_to_dict(row)
    finally:
        conn.close()


def get_latest_baseline(db_path: Path | None = None) -> dict | None:
    """Get the most recent baseline snapshot."""
    conn = _get_conn(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM snapshots WHERE is_baseline = 1 ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        return _row_to_dict(row)
    finally:
        conn.close()


def list_snapshots(db_path: Path | None = None) -> list[dict]:
    """List all snapshots (metadata only, no data blob)."""
    conn = _get_conn(db_path)
    try:
        rows = conn.execute(
            "SELECT id, name, timestamp, is_baseline FROM snapshots ORDER BY id DESC"
        ).fetchall()
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "timestamp": row["timestamp"],
                "is_baseline": bool(row["is_baseline"]),
            }
            for row in rows
        ]
    finally:
        conn.close()


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a database row to a dict with parsed JSON data."""
    return {
        "id": row["id"],
        "name": row["name"],
        "timestamp": row["timestamp"],
        "data": json.loads(row["data"]),
        "is_baseline": bool(row["is_baseline"]),
    }
