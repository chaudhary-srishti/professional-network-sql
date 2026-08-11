"""asyncpg connection pool + a FastAPI dependency that hands routers a live connection.

Everything below the router layer speaks raw SQL through an ``asyncpg.Connection``. Values are
always passed as positional ``$1, $2, ...`` parameters — never string-formatted — so the
queries are injection-safe.
"""
from __future__ import annotations

from typing import AsyncIterator

import asyncpg

from .config import get_settings

_pool: asyncpg.Pool | None = None


async def create_pool() -> asyncpg.Pool:
    """Create the process-wide pool. Called once from the app lifespan."""
    global _pool
    settings = get_settings()
    _pool = await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=settings.db_pool_min,
        max_size=settings.db_pool_max,
    )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:  # pragma: no cover - guards misuse outside the app lifespan
        raise RuntimeError("Database pool is not initialized")
    return _pool


async def get_conn() -> AsyncIterator[asyncpg.Connection]:
    """FastAPI dependency: acquire a connection for the duration of one request."""
    async with get_pool().acquire() as conn:
        yield conn
