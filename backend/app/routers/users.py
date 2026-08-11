"""users routes."""
from __future__ import annotations

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, Query, Response

from ..db import get_conn
from ..errors import DomainError
from ..repositories import posts as posts_repo
from ..repositories import users as users_repo
from ..schemas import PostFeedOut, UserCreate, UserOut, UserStatsOut, UserUpdate
from ..security import current_user
from . import require, rows

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserOut, status_code=201)
async def create_user(body: UserCreate, conn: asyncpg.Connection = Depends(get_conn)):
    """Get-or-create by email (public — this is how a user first appears)."""
    return dict(await users_repo.create_or_get(conn, body.model_dump()))


@router.get("", response_model=list[UserOut])
async def list_users(
    q: str | None = Query(default=None, description="partial name match (pg_trgm)"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    conn: asyncpg.Connection = Depends(get_conn),
):
    return rows(await users_repo.search(conn, q, limit, offset))


@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: UUID, conn: asyncpg.Connection = Depends(get_conn)):
    return require(await users_repo.get(conn, user_id), "User not found")


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: UUID,
    body: UserUpdate,
    conn: asyncpg.Connection = Depends(get_conn),
    me: asyncpg.Record = Depends(current_user),
):
    if me["id"] != user_id and not me["super_admin"]:
        raise DomainError(403, "Cannot update another user")
    fields = body.model_dump(exclude_unset=True)
    return require(await users_repo.update(conn, user_id, fields), "User not found")


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
    me: asyncpg.Record = Depends(current_user),
):
    if me["id"] != user_id and not me["super_admin"]:
        raise DomainError(403, "Cannot delete another user")
    if not await users_repo.delete(conn, user_id):
        raise DomainError(404, "User not found")
    return Response(status_code=204)


@router.get("/{user_id}/stats", response_model=UserStatsOut)
async def user_stats(user_id: UUID, conn: asyncpg.Connection = Depends(get_conn)):
    return require(await users_repo.stats(conn, user_id), "User not found")


@router.get("/{user_id}/posts", response_model=list[PostFeedOut])
async def user_posts(
    user_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    conn: asyncpg.Connection = Depends(get_conn),
):
    return rows(await posts_repo.list_by_author(conn, user_id, limit, offset))
