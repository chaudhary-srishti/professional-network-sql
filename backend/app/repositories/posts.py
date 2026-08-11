"""posts repository. Reads go through the post_feed view (author + firm + counts resolved)."""
from __future__ import annotations

from typing import Any
from uuid import UUID

import asyncpg

from . import build_set_clause

_UPDATABLE = {"hashtags", "images", "shared_post_id", "shared_article_id"}


async def create(conn: asyncpg.Connection, author_id: UUID, data: dict[str, Any]) -> asyncpg.Record:
    row = await conn.fetchrow(
        """INSERT INTO posts (author_id, firm_id, hashtags, images, shared_post_id, shared_article_id)
           VALUES ($1, $2, $3, $4, $5, $6) RETURNING id""",
        author_id, data.get("firm_id"), data.get("hashtags") or [], data.get("images") or [],
        data.get("shared_post_id"), data.get("shared_article_id"),
    )
    return await get_feed_one(conn, row["id"])


async def get_feed_one(conn: asyncpg.Connection, post_id: UUID) -> asyncpg.Record | None:
    return await conn.fetchrow("SELECT * FROM post_feed WHERE id = $1", post_id)


async def list_feed(
    conn: asyncpg.Connection, hashtag: str | None, limit: int, offset: int
) -> list[asyncpg.Record]:
    return await conn.fetch(
        """SELECT * FROM post_feed
           WHERE ($1::text IS NULL OR hashtags @> ARRAY[$1]::text[])
           ORDER BY updated_at DESC LIMIT $2 OFFSET $3""",
        hashtag, limit, offset,
    )


async def list_by_author(
    conn: asyncpg.Connection, author_id: UUID, limit: int, offset: int
) -> list[asyncpg.Record]:
    return await conn.fetch(
        "SELECT * FROM post_feed WHERE author_id = $1 ORDER BY updated_at DESC LIMIT $2 OFFSET $3",
        author_id, limit, offset,
    )


async def list_by_firm(
    conn: asyncpg.Connection, firm_id: UUID, limit: int, offset: int
) -> list[asyncpg.Record]:
    return await conn.fetch(
        "SELECT * FROM post_feed WHERE firm_id = $1 ORDER BY updated_at DESC LIMIT $2 OFFSET $3",
        firm_id, limit, offset,
    )


async def update(
    conn: asyncpg.Connection, post_id: UUID, author_id: UUID, fields: dict[str, Any]
) -> asyncpg.Record | None:
    fields = {k: v for k, v in fields.items() if k in _UPDATABLE}
    if not fields:
        return await get_feed_one(conn, post_id)
    set_sql, vals, nxt = build_set_clause(fields)
    # Ownership enforced in the WHERE: a non-author update matches 0 rows.
    row = await conn.fetchrow(
        f"UPDATE posts SET {set_sql} WHERE id = ${nxt} AND author_id = ${nxt + 1} RETURNING id",
        *vals, post_id, author_id,
    )
    if row is None:
        return None
    return await get_feed_one(conn, post_id)


async def delete(conn: asyncpg.Connection, post_id: UUID, author_id: UUID) -> bool:
    """Author-only delete (fixes the doc's 'any user can delete any post' bug)."""
    row = await conn.fetchrow(
        "DELETE FROM posts WHERE id = $1 AND author_id = $2 RETURNING id",
        post_id, author_id,
    )
    return row is not None


async def exists(conn: asyncpg.Connection, post_id: UUID) -> bool:
    return await conn.fetchval("SELECT true FROM posts WHERE id = $1", post_id) or False
