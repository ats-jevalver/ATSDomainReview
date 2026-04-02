"""SQLite database setup with aiosqlite."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import aiosqlite

from config import app_settings

_CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS scans (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed'))
);

CREATE TABLE IF NOT EXISTS domain_results (
    id TEXT PRIMARY KEY,
    scan_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    raw_data TEXT,
    score INTEGER,
    risk_level TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_domain_results_scan_id ON domain_results(scan_id);
CREATE INDEX IF NOT EXISTS idx_domain_results_domain ON domain_results(domain);
"""

# ---------------------------------------------------------------------------
# Lazy-initialised shared connection and lock.
# The lock MUST be created inside the running event loop (not at import time)
# to avoid the Python 3.9 "Future attached to a different loop" error.
# ---------------------------------------------------------------------------
_db: aiosqlite.Connection | None = None
_db_lock: asyncio.Lock | None = None


def _get_lock() -> asyncio.Lock:
    """Return the DB lock, creating it on first call inside the running loop."""
    global _db_lock
    if _db_lock is None:
        _db_lock = asyncio.Lock()
    return _db_lock


async def _get_db() -> aiosqlite.Connection:
    """Return the shared database connection, creating it if needed."""
    global _db
    if _db is None:
        _db = await aiosqlite.connect(app_settings.database_path)
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA busy_timeout=5000")
    return _db


async def init_database() -> None:
    """Create database tables if they do not exist."""
    lock = _get_lock()
    async with lock:
        db = await _get_db()
        await db.executescript(_CREATE_TABLES_SQL)
        await db.commit()


async def close_database() -> None:
    """Close the shared database connection."""
    global _db, _db_lock
    if _db is not None:
        await _db.close()
        _db = None
    _db_lock = None


async def create_scan(scan_id: str) -> None:
    """Insert a new scan record."""
    lock = _get_lock()
    async with lock:
        db = await _get_db()
        await db.execute("INSERT INTO scans (id, status) VALUES (?, 'pending')", (scan_id,))
        await db.commit()


async def update_scan_status(scan_id: str, status: str) -> None:
    """Update the status of a scan."""
    lock = _get_lock()
    async with lock:
        db = await _get_db()
        await db.execute("UPDATE scans SET status = ? WHERE id = ?", (status, scan_id))
        await db.commit()


async def get_scan(scan_id: str) -> dict[str, Any] | None:
    """Retrieve a scan by ID."""
    lock = _get_lock()
    async with lock:
        db = await _get_db()
        cursor = await db.execute("SELECT * FROM scans WHERE id = ?", (scan_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)


async def insert_domain_result(
    result_id: str,
    scan_id: str,
    domain: str,
    status: str,
    raw_data: dict | None = None,
    score: int | None = None,
    risk_level: str | None = None,
) -> None:
    """Insert or update a domain result."""
    lock = _get_lock()
    async with lock:
        db = await _get_db()
        await db.execute(
            """INSERT INTO domain_results (id, scan_id, domain, status, raw_data, score, risk_level)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                   status = excluded.status,
                   raw_data = COALESCE(excluded.raw_data, domain_results.raw_data),
                   score = COALESCE(excluded.score, domain_results.score),
                   risk_level = COALESCE(excluded.risk_level, domain_results.risk_level)""",
            (result_id, scan_id, domain, status, json.dumps(raw_data) if raw_data else None, score, risk_level),
        )
        await db.commit()


async def get_domain_results(scan_id: str) -> list[dict[str, Any]]:
    """Retrieve all domain results for a scan."""
    lock = _get_lock()
    async with lock:
        db = await _get_db()
        cursor = await db.execute(
            "SELECT * FROM domain_results WHERE scan_id = ? ORDER BY created_at",
            (scan_id,),
        )
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            d = dict(row)
            if d.get("raw_data"):
                d["raw_data"] = json.loads(d["raw_data"])
            results.append(d)
        return results


async def get_latest_domain_result(domain: str) -> dict[str, Any] | None:
    """Retrieve the most recent result for a specific domain."""
    lock = _get_lock()
    async with lock:
        db = await _get_db()
        cursor = await db.execute(
            "SELECT * FROM domain_results WHERE domain = ? ORDER BY created_at DESC LIMIT 1",
            (domain,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        d = dict(row)
        if d.get("raw_data"):
            d["raw_data"] = json.loads(d["raw_data"])
        return d


async def get_scan_progress(scan_id: str) -> dict[str, int]:
    """Get the total and completed count for a scan."""
    lock = _get_lock()
    async with lock:
        db = await _get_db()
        cursor = await db.execute(
            "SELECT COUNT(*) as total, SUM(CASE WHEN status IN ('completed', 'failed') THEN 1 ELSE 0 END) as completed FROM domain_results WHERE scan_id = ?",
            (scan_id,),
        )
        row = await cursor.fetchone()
        return {"total": row["total"] or 0, "completed": row["completed"] or 0}
