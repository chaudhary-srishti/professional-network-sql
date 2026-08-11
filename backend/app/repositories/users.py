"""users repository."""
from __future__ import annotations

from typing import Any
from uuid import UUID

import asyncpg

from . import build_set_clause

_COLS = (
    "id, email, name, current_title, current_company, bio, profile_picture, cover_photo, "
    "location_street, location_city, location_state, location_country, location_postal_code, "
    "location_longitude, location_latitude, super_admin, created_at, updated_at, last_login"
)


async def create_or_get(conn: asyncpg.Connection, data: dict[str, Any]) -> asyncpg.Record:
    """Get-or-create by email (the Mongo get_or_create_user upsert). Refreshes last_login."""
    return await conn.fetchrow(
        f"""
        INSERT INTO users (email, name, current_title, current_company, bio, profile_picture,
                           cover_photo, location_street, location_city, location_state,
                           location_country, location_postal_code, location_longitude,
                           location_latitude, last_login)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14, now())
        ON CONFLICT (email) DO UPDATE SET last_login = now()
        RETURNING {_COLS}
        """,
        data.get("email"), data.get("name"), data.get("current_title"),
        data.get("current_company"), data.get("bio"), data.get("profile_picture"),
        data.get("cover_photo"), data.get("location_street"), data.get("location_city"),
        data.get("location_state"), data.get("location_country"),
        data.get("location_postal_code"), data.get("location_longitude"),
        data.get("location_latitude"),
    )


async def get(conn: asyncpg.Connection, user_id: UUID) -> asyncpg.Record | None:
    return await conn.fetchrow(f"SELECT {_COLS} FROM users WHERE id = $1", user_id)


async def search(
    conn: asyncpg.Connection, q: str | None, limit: int, offset: int
) -> list[asyncpg.Record]:
    return await conn.fetch(
        f"""
        SELECT {_COLS} FROM users
        WHERE ($1::text IS NULL OR name ILIKE '%' || $1 || '%')
        ORDER BY CASE WHEN $1::text IS NULL THEN 0 ELSE similarity(name, $1) END DESC,
                 created_at DESC
        LIMIT $2 OFFSET $3
        """,
        q, limit, offset,
    )


async def update(
    conn: asyncpg.Connection, user_id: UUID, fields: dict[str, Any]
) -> asyncpg.Record | None:
    if not fields:
        return await get(conn, user_id)
    set_sql, vals, nxt = build_set_clause(fields)
    return await conn.fetchrow(
        f"UPDATE users SET {set_sql} WHERE id = ${nxt} RETURNING {_COLS}",
        *vals, user_id,
    )


async def delete(conn: asyncpg.Connection, user_id: UUID) -> bool:
    row = await conn.fetchrow("DELETE FROM users WHERE id = $1 RETURNING id", user_id)
    return row is not None


async def stats(conn: asyncpg.Connection, user_id: UUID) -> asyncpg.Record | None:
    return await conn.fetchrow("SELECT * FROM user_stats WHERE user_id = $1", user_id)
