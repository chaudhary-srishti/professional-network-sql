"""Development authentication.

The product's real auth is Firebase; every router "resolves the authenticated Firebase user ->
user by email". We mirror that shape with a header: `X-User-Email` identifies the caller, and we
resolve it to the users row. Mutations take the actor from *this* dependency, never from the
request body — the fix for the doc's "engagement writes trust user_id from the body" bug.

Swap `current_user` for a real JWT verifier in production; nothing else needs to change.
"""
from __future__ import annotations

import asyncpg
from fastapi import Depends, Header

from .db import get_conn
from .errors import DomainError


async def current_user(
    x_user_email: str | None = Header(default=None, alias="X-User-Email"),
    conn: asyncpg.Connection = Depends(get_conn),
) -> asyncpg.Record:
    if not x_user_email:
        raise DomainError(401, "Missing X-User-Email header")
    row = await conn.fetchrow(
        "SELECT id, email, name, super_admin FROM users WHERE email = $1",
        x_user_email,
    )
    if row is None:
        raise DomainError(401, "Unknown user for X-User-Email")
    return row
