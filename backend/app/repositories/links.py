"""Social graph: user_connections, organization_follows, firm_member_requests."""
from __future__ import annotations

from uuid import UUID

import asyncpg

_CONN_COLS = ("id, requester_id, target_id, status, personal_note, status_updated_at, "
              "created_at, updated_at")
_REQ_COLS = ("id, user_id, organization_id, status, personal_note, status_updated_at, "
             "created_at, updated_at")


# --- user connections ------------------------------------------------------------------------
async def create_connection(
    conn: asyncpg.Connection, requester_id: UUID, target_id: UUID, note: str | None
) -> asyncpg.Record:
    return await conn.fetchrow(
        f"""INSERT INTO user_connections (requester_id, target_id, personal_note)
            VALUES ($1, $2, $3) RETURNING {_CONN_COLS}""",
        requester_id, target_id, note,
    )


async def respond_connection(
    conn: asyncpg.Connection, connection_id: UUID, actor_id: UUID, new_status: str
) -> asyncpg.Record | None:
    """Only the target may accept/reject, and only while pending — enforced in the WHERE."""
    return await conn.fetchrow(
        f"""UPDATE user_connections SET status = $3, status_updated_at = now()
            WHERE id = $1 AND target_id = $2 AND status = 'pending'
            RETURNING {_CONN_COLS}""",
        connection_id, actor_id, new_status,
    )


async def delete_connection(
    conn: asyncpg.Connection, connection_id: UUID, actor_id: UUID
) -> bool:
    row = await conn.fetchrow(
        """DELETE FROM user_connections
           WHERE id = $1 AND (requester_id = $2 OR target_id = $2) RETURNING id""",
        connection_id, actor_id,
    )
    return row is not None


async def list_edges(
    conn: asyncpg.Connection, user_id: UUID, status: str | None
) -> list[asyncpg.Record]:
    return await conn.fetch(
        """SELECT id, user_id, other_user_id, direction, status, created_at
           FROM user_connection_edges
           WHERE user_id = $1 AND ($2::text IS NULL OR status = $2)
           ORDER BY created_at DESC""",
        user_id, status,
    )


# --- follows ---------------------------------------------------------------------------------
async def follow(conn: asyncpg.Connection, user_id: UUID, org_id: UUID) -> asyncpg.Record:
    row = await conn.fetchrow(
        """INSERT INTO organization_follows (user_id, organization_id) VALUES ($1, $2)
           ON CONFLICT (user_id, organization_id) DO NOTHING
           RETURNING id, user_id, organization_id, created_at""",
        user_id, org_id,
    )
    if row is None:  # already following -> return the existing edge (idempotent)
        row = await conn.fetchrow(
            """SELECT id, user_id, organization_id, created_at FROM organization_follows
               WHERE user_id = $1 AND organization_id = $2""",
            user_id, org_id,
        )
    return row


async def unfollow(conn: asyncpg.Connection, user_id: UUID, org_id: UUID) -> bool:
    row = await conn.fetchrow(
        "DELETE FROM organization_follows WHERE user_id = $1 AND organization_id = $2 RETURNING id",
        user_id, org_id,
    )
    return row is not None


async def list_following(conn: asyncpg.Connection, user_id: UUID) -> list[asyncpg.Record]:
    return await conn.fetch(
        "SELECT id, user_id, organization_id, created_at FROM organization_follows "
        "WHERE user_id = $1 ORDER BY created_at DESC",
        user_id,
    )


async def list_followers(conn: asyncpg.Connection, org_id: UUID) -> list[asyncpg.Record]:
    return await conn.fetch(
        "SELECT id, user_id, organization_id, created_at FROM organization_follows "
        "WHERE organization_id = $1 ORDER BY created_at DESC",
        org_id,
    )


# --- firm member requests --------------------------------------------------------------------
async def create_member_request(
    conn: asyncpg.Connection, user_id: UUID, org_id: UUID, note: str | None
) -> asyncpg.Record:
    return await conn.fetchrow(
        f"""INSERT INTO firm_member_requests (user_id, organization_id, personal_note)
            VALUES ($1, $2, $3) RETURNING {_REQ_COLS}""",
        user_id, org_id, note,
    )


async def respond_member_request(
    conn: asyncpg.Connection, request_id: UUID, actor_id: UUID, new_status: str
) -> asyncpg.Record | None:
    """Only an 'owner' member of the target firm may respond. On accept, add the membership.

    Wrapped in a transaction so the status change and the membership insert commit together.
    """
    async with conn.transaction():
        row = await conn.fetchrow(
            f"""UPDATE firm_member_requests r SET status = $3, status_updated_at = now()
                WHERE r.id = $1 AND r.status = 'pending'
                  AND EXISTS (
                      SELECT 1 FROM organization_members m
                      WHERE m.organization_id = r.organization_id
                        AND m.user_id = $2 AND m.role = 'owner')
                RETURNING {_REQ_COLS}""",
            request_id, actor_id, new_status,
        )
        if row is not None and new_status == "accepted":
            await conn.execute(
                """INSERT INTO organization_members (organization_id, user_id, role)
                   VALUES ($1, $2, 'member')
                   ON CONFLICT (organization_id, user_id) DO NOTHING""",
                row["organization_id"], row["user_id"],
            )
    return row
