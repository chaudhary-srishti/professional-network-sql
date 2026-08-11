"""organizations + organization_members repository."""
from __future__ import annotations

from typing import Any
from uuid import UUID

import asyncpg

from . import build_set_clause

_COLS = (
    "id, firm_url, name, description, overview, logo, cover_photo, size, categories, "
    "location_street, location_city, location_state, location_country, location_postal_code, "
    "location_longitude, location_latitude, created_at, updated_at"
)


async def create(conn: asyncpg.Connection, data: dict[str, Any]) -> asyncpg.Record:
    """Insert a firm. firm_url is filled by the generate_firm_url trigger (not client-set)."""
    cols = list(data.keys())
    placeholders = ", ".join(f"${i}" for i in range(1, len(cols) + 1))
    return await conn.fetchrow(
        f"INSERT INTO organizations ({', '.join(cols)}) VALUES ({placeholders}) RETURNING {_COLS}",
        *data.values(),
    )


async def get(conn: asyncpg.Connection, org_id: UUID) -> asyncpg.Record | None:
    return await conn.fetchrow(f"SELECT {_COLS} FROM organizations WHERE id = $1", org_id)


async def search(
    conn: asyncpg.Connection, q: str | None, category: str | None, limit: int, offset: int
) -> list[asyncpg.Record]:
    return await conn.fetch(
        f"""
        SELECT {_COLS} FROM organizations
        WHERE ($1::text IS NULL OR name ILIKE '%' || $1 || '%')
          AND ($2::text IS NULL OR $2 = ANY(categories))
        ORDER BY created_at DESC
        LIMIT $3 OFFSET $4
        """,
        q, category, limit, offset,
    )


async def update(
    conn: asyncpg.Connection, org_id: UUID, fields: dict[str, Any]
) -> asyncpg.Record | None:
    if not fields:
        return await get(conn, org_id)
    set_sql, vals, nxt = build_set_clause(fields)
    return await conn.fetchrow(
        f"UPDATE organizations SET {set_sql} WHERE id = ${nxt} RETURNING {_COLS}",
        *vals, org_id,
    )


async def delete(conn: asyncpg.Connection, org_id: UUID) -> bool:
    row = await conn.fetchrow("DELETE FROM organizations WHERE id = $1 RETURNING id", org_id)
    return row is not None


async def stats(conn: asyncpg.Connection, org_id: UUID) -> asyncpg.Record | None:
    return await conn.fetchrow("SELECT * FROM firm_stats WHERE firm_id = $1", org_id)


# --- members ---------------------------------------------------------------------------------
async def add_member(
    conn: asyncpg.Connection, org_id: UUID, user_id: UUID, role: str
) -> asyncpg.Record:
    return await conn.fetchrow(
        """
        INSERT INTO organization_members (organization_id, user_id, role)
        VALUES ($1, $2, $3)
        ON CONFLICT (organization_id, user_id) DO UPDATE SET role = EXCLUDED.role
        RETURNING organization_id, user_id, role, added_at
        """,
        org_id, user_id, role,
    )


async def remove_member(conn: asyncpg.Connection, org_id: UUID, user_id: UUID) -> bool:
    row = await conn.fetchrow(
        "DELETE FROM organization_members WHERE organization_id = $1 AND user_id = $2 RETURNING user_id",
        org_id, user_id,
    )
    return row is not None


async def list_members(conn: asyncpg.Connection, org_id: UUID) -> list[asyncpg.Record]:
    return await conn.fetch(
        "SELECT organization_id, user_id, role, added_at FROM organization_members "
        "WHERE organization_id = $1 ORDER BY added_at",
        org_id,
    )
