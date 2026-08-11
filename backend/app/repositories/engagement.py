"""Engagement: comments (replies) and likes. Counters are maintained by DB triggers, so this
layer never writes like_count / comment_count directly."""
from __future__ import annotations

from uuid import UUID

import asyncpg

_COMMENT_COLS = "id, author_id, firm_id, post_id, article_id, body, like_count, created_at, updated_at"

# target kind -> (like FK column, owning table). Keys are code-controlled, never client input.
_TARGETS = {
    "post": ("post_id", "posts"),
    "article": ("article_id", "articles"),
    "comment": ("comment_id", "comments"),
}


# --- comments --------------------------------------------------------------------------------
async def add_comment(
    conn: asyncpg.Connection,
    author_id: UUID,
    body: str,
    *,
    post_id: UUID | None = None,
    article_id: UUID | None = None,
) -> asyncpg.Record:
    return await conn.fetchrow(
        f"""INSERT INTO comments (author_id, post_id, article_id, body)
            VALUES ($1, $2, $3, $4) RETURNING {_COMMENT_COLS}""",
        author_id, post_id, article_id, body,
    )


async def list_comments(
    conn: asyncpg.Connection, *, post_id: UUID | None = None, article_id: UUID | None = None
) -> list[asyncpg.Record]:
    if post_id is not None:
        return await conn.fetch(
            f"SELECT {_COMMENT_COLS} FROM comments WHERE post_id = $1 ORDER BY created_at",
            post_id,
        )
    return await conn.fetch(
        f"SELECT {_COMMENT_COLS} FROM comments WHERE article_id = $1 ORDER BY created_at",
        article_id,
    )


async def delete_comment(conn: asyncpg.Connection, comment_id: UUID, author_id: UUID) -> bool:
    row = await conn.fetchrow(
        "DELETE FROM comments WHERE id = $1 AND author_id = $2 RETURNING id",
        comment_id, author_id,
    )
    return row is not None


# --- likes -----------------------------------------------------------------------------------
async def like(
    conn: asyncpg.Connection, user_id: UUID, target: str, target_id: UUID
) -> tuple[bool, int]:
    col, table = _TARGETS[target]
    # ON CONFLICT against the per-target partial unique index makes a double-tap idempotent.
    await conn.execute(
        f"""INSERT INTO likes (user_id, {col}) VALUES ($1, $2)
            ON CONFLICT (user_id, {col}) WHERE {col} IS NOT NULL DO NOTHING""",
        user_id, target_id,
    )
    count = await conn.fetchval(f"SELECT like_count FROM {table} WHERE id = $1", target_id)
    return True, count or 0


async def unlike(
    conn: asyncpg.Connection, user_id: UUID, target: str, target_id: UUID
) -> tuple[bool, int]:
    col, table = _TARGETS[target]
    await conn.execute(
        f"DELETE FROM likes WHERE user_id = $1 AND {col} = $2", user_id, target_id
    )
    count = await conn.fetchval(f"SELECT like_count FROM {table} WHERE id = $1", target_id)
    return False, count or 0
