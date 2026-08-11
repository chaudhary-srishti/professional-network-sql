"""Engagement routes: comments (replies) and likes on posts/articles/comments."""
from __future__ import annotations

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, Response

from ..db import get_conn
from ..errors import DomainError
from ..repositories import engagement as eng_repo
from ..schemas import CommentCreate, CommentOut, LikeResult
from ..security import current_user
from . import rows

router = APIRouter(tags=["engagement"])


# --- comments --------------------------------------------------------------------------------
@router.post("/posts/{post_id}/comments", response_model=CommentOut, status_code=201)
async def comment_on_post(
    post_id: UUID,
    body: CommentCreate,
    conn: asyncpg.Connection = Depends(get_conn),
    me: asyncpg.Record = Depends(current_user),
):
    return dict(await eng_repo.add_comment(conn, me["id"], body.body, post_id=post_id))


@router.get("/posts/{post_id}/comments", response_model=list[CommentOut])
async def list_post_comments(post_id: UUID, conn: asyncpg.Connection = Depends(get_conn)):
    return rows(await eng_repo.list_comments(conn, post_id=post_id))


@router.post("/articles/{article_id}/comments", response_model=CommentOut, status_code=201)
async def comment_on_article(
    article_id: UUID,
    body: CommentCreate,
    conn: asyncpg.Connection = Depends(get_conn),
    me: asyncpg.Record = Depends(current_user),
):
    return dict(await eng_repo.add_comment(conn, me["id"], body.body, article_id=article_id))


@router.get("/articles/{article_id}/comments", response_model=list[CommentOut])
async def list_article_comments(article_id: UUID, conn: asyncpg.Connection = Depends(get_conn)):
    return rows(await eng_repo.list_comments(conn, article_id=article_id))


@router.delete("/comments/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
    me: asyncpg.Record = Depends(current_user),
):
    if not await eng_repo.delete_comment(conn, comment_id, me["id"]):
        raise DomainError(403, "Comment not found or not yours")
    return Response(status_code=204)


# --- likes (create = POST, remove = DELETE; both return the current state) -------------------
async def _like(conn, me, target, target_id) -> LikeResult:
    liked, count = await eng_repo.like(conn, me["id"], target, target_id)
    return LikeResult(liked=liked, like_count=count)


async def _unlike(conn, me, target, target_id) -> LikeResult:
    liked, count = await eng_repo.unlike(conn, me["id"], target, target_id)
    return LikeResult(liked=liked, like_count=count)


@router.post("/posts/{post_id}/likes", response_model=LikeResult)
async def like_post(post_id: UUID, conn=Depends(get_conn), me=Depends(current_user)):
    return await _like(conn, me, "post", post_id)


@router.delete("/posts/{post_id}/likes", response_model=LikeResult)
async def unlike_post(post_id: UUID, conn=Depends(get_conn), me=Depends(current_user)):
    return await _unlike(conn, me, "post", post_id)


@router.post("/articles/{article_id}/likes", response_model=LikeResult)
async def like_article(article_id: UUID, conn=Depends(get_conn), me=Depends(current_user)):
    return await _like(conn, me, "article", article_id)


@router.delete("/articles/{article_id}/likes", response_model=LikeResult)
async def unlike_article(article_id: UUID, conn=Depends(get_conn), me=Depends(current_user)):
    return await _unlike(conn, me, "article", article_id)


@router.post("/comments/{comment_id}/likes", response_model=LikeResult)
async def like_comment(comment_id: UUID, conn=Depends(get_conn), me=Depends(current_user)):
    """A like on a reply — the self-referential reply_like."""
    return await _like(conn, me, "comment", comment_id)


@router.delete("/comments/{comment_id}/likes", response_model=LikeResult)
async def unlike_comment(comment_id: UUID, conn=Depends(get_conn), me=Depends(current_user)):
    return await _unlike(conn, me, "comment", comment_id)
