"""PostgreSQL database setup with asyncpg."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import asyncpg

from config import app_settings

_CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS scans (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed'))
);

CREATE TABLE IF NOT EXISTS domain_results (
    id TEXT PRIMARY KEY,
    scan_id TEXT NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    domain TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    raw_data JSONB,
    score INTEGER,
    risk_level TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_domain_results_scan_id ON domain_results(scan_id);
CREATE INDEX IF NOT EXISTS idx_domain_results_domain ON domain_results(domain);
"""

# ---------------------------------------------------------------------------
# Lazy-initialised shared connection pool.
# ---------------------------------------------------------------------------
_pool: asyncpg.Pool | None = None


async def _get_pool() -> asyncpg.Pool:
    """Return the shared connection pool, creating it if needed."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=app_settings.database_url,
            min_size=2,
            max_size=10,
        )
    return _pool


async def init_database() -> None:
    """Create database tables if they do not exist."""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute(_CREATE_TABLES_SQL)


async def close_database() -> None:
    """Close the shared connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def create_scan(scan_id: str) -> None:
    """Insert a new scan record."""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO scans (id, status) VALUES ($1, 'pending')", scan_id
        )


async def update_scan_status(scan_id: str, status: str) -> None:
    """Update the status of a scan."""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE scans SET status = $1 WHERE id = $2", status, scan_id
        )


async def get_scan(scan_id: str) -> dict[str, Any] | None:
    """Retrieve a scan by ID."""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM scans WHERE id = $1", scan_id)
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
    pool = await _get_pool()
    raw_json = json.dumps(raw_data) if raw_data else None
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO domain_results (id, scan_id, domain, status, raw_data, score, risk_level)
               VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7)
               ON CONFLICT (id) DO UPDATE SET
                   status = EXCLUDED.status,
                   raw_data = COALESCE(EXCLUDED.raw_data, domain_results.raw_data),
                   score = COALESCE(EXCLUDED.score, domain_results.score),
                   risk_level = COALESCE(EXCLUDED.risk_level, domain_results.risk_level)""",
            result_id, scan_id, domain, status, raw_json, score, risk_level,
        )


async def get_domain_results(scan_id: str) -> list[dict[str, Any]]:
    """Retrieve all domain results for a scan."""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM domain_results WHERE scan_id = $1 ORDER BY created_at",
            scan_id,
        )
        results = []
        for row in rows:
            d = dict(row)
            # asyncpg auto-deserialises JSONB, but normalise for callers
            if d.get("raw_data") and isinstance(d["raw_data"], str):
                d["raw_data"] = json.loads(d["raw_data"])
            results.append(d)
        return results


async def get_latest_domain_result(domain: str) -> dict[str, Any] | None:
    """Retrieve the most recent result for a specific domain."""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM domain_results WHERE domain = $1 ORDER BY created_at DESC LIMIT 1",
            domain,
        )
        if row is None:
            return None
        d = dict(row)
        if d.get("raw_data") and isinstance(d["raw_data"], str):
            d["raw_data"] = json.loads(d["raw_data"])
        return d


async def get_scan_progress(scan_id: str) -> dict[str, int]:
    """Get the total and completed count for a scan."""
    pool = await _get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT COUNT(*) as total,
                      SUM(CASE WHEN status IN ('completed', 'failed') THEN 1 ELSE 0 END) as completed
               FROM domain_results WHERE scan_id = $1""",
            scan_id,
        )
        return {"total": row["total"] or 0, "completed": row["completed"] or 0}
