"""articles repository. Reads go through the article_feed view."""
from __future__ import annotations

from typing import Any
from uuid import UUID

import asyncpg

from . import build_set_clause

_UPDATABLE = {"cover_image", "images"}


async def create(conn: asyncpg.Connection, author_id: UUID, data: dict[str, Any]) -> asyncpg.Record:
    row = await conn.fetchrow(
        """INSERT INTO articles (author_id, firm_id, cover_image, images)
           VALUES ($1, $2, $3, $4) RETURNING id""",
        author_id, data.get("firm_id"), data.get("cover_image"), data.get("images") or [],
    )
    return await get_feed_one(conn, row["id"])


async def get_feed_one(conn: asyncpg.Connection, article_id: UUID) -> asyncpg.Record | None:
    return await conn.fetchrow("SELECT * FROM article_feed WHERE id = $1", article_id)


async def list_feed(conn: asyncpg.Connection, limit: int, offset: int) -> list[asyncpg.Record]:
    return await conn.fetch(
        "SELECT * FROM article_feed ORDER BY updated_at DESC LIMIT $1 OFFSET $2", limit, offset
    )


async def list_by_author(
    conn: asyncpg.Connection, author_id: UUID, limit: int, offset: int
) -> list[asyncpg.Record]:
    return await conn.fetch(
        "SELECT * FROM article_feed WHERE author_id = $1 ORDER BY updated_at DESC LIMIT $2 OFFSET $3",
        author_id, limit, offset,
    )


async def update(
    conn: asyncpg.Connection, article_id: UUID, author_id: UUID, fields: dict[str, Any]
) -> asyncpg.Record | None:
    fields = {k: v for k, v in fields.items() if k in _UPDATABLE}
    if not fields:
        return await get_feed_one(conn, article_id)
    set_sql, vals, nxt = build_set_clause(fields)
    row = await conn.fetchrow(
        f"UPDATE articles SET {set_sql} WHERE id = ${nxt} AND author_id = ${nxt + 1} RETURNING id",
        *vals, article_id, author_id,
    )
    if row is None:
        return None
    return await get_feed_one(conn, article_id)


async def delete(conn: asyncpg.Connection, article_id: UUID, author_id: UUID) -> bool:
    row = await conn.fetchrow(
        "DELETE FROM articles WHERE id = $1 AND author_id = $2 RETURNING id",
        article_id, author_id,
    )
    return row is not None
