"""posts routes."""
from __future__ import annotations

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, Query, Response

from ..db import get_conn
from ..errors import DomainError
from ..repositories import posts as posts_repo
from ..schemas import PostCreate, PostFeedOut, PostUpdate
from ..security import current_user
from . import require, rows

router = APIRouter(prefix="/posts", tags=["posts"])


@router.post("", response_model=PostFeedOut, status_code=201)
async def create_post(
    body: PostCreate,
    conn: asyncpg.Connection = Depends(get_conn),
    me: asyncpg.Record = Depends(current_user),
):
    return dict(await posts_repo.create(conn, me["id"], body.model_dump()))


@router.get("", response_model=list[PostFeedOut])
async def feed(
    hashtag: str | None = Query(default=None, description="filter to posts containing this hashtag"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    conn: asyncpg.Connection = Depends(get_conn),
):
    return rows(await posts_repo.list_feed(conn, hashtag, limit, offset))


@router.get("/{post_id}", response_model=PostFeedOut)
async def get_post(post_id: UUID, conn: asyncpg.Connection = Depends(get_conn)):
    return require(await posts_repo.get_feed_one(conn, post_id), "Post not found")


@router.patch("/{post_id}", response_model=PostFeedOut)
async def update_post(
    post_id: UUID,
    body: PostUpdate,
    conn: asyncpg.Connection = Depends(get_conn),
    me: asyncpg.Record = Depends(current_user),
):
    updated = await posts_repo.update(conn, post_id, me["id"], body.model_dump(exclude_unset=True))
    if updated is None:
        # Distinguish "no such post" from "not your post".
        if await posts_repo.get_feed_one(conn, post_id) is not None:
            raise DomainError(403, "Not the author of this post")
        raise DomainError(404, "Post not found")
    return dict(updated)


@router.delete("/{post_id}", status_code=204)
async def delete_post(
    post_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
    me: asyncpg.Record = Depends(current_user),
):
    if not await posts_repo.delete(conn, post_id, me["id"]):
        if await posts_repo.get_feed_one(conn, post_id) is not None:
            raise DomainError(403, "Not the author of this post")
        raise DomainError(404, "Post not found")
    return Response(status_code=204)
