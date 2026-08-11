"""articles routes."""
from __future__ import annotations

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, Query, Response

from ..db import get_conn
from ..errors import DomainError
from ..repositories import articles as articles_repo
from ..schemas import ArticleCreate, ArticleFeedOut, ArticleUpdate
from ..security import current_user
from . import require, rows

router = APIRouter(prefix="/articles", tags=["articles"])


@router.post("", response_model=ArticleFeedOut, status_code=201)
async def create_article(
    body: ArticleCreate,
    conn: asyncpg.Connection = Depends(get_conn),
    me: asyncpg.Record = Depends(current_user),
):
    return dict(await articles_repo.create(conn, me["id"], body.model_dump()))


@router.get("", response_model=list[ArticleFeedOut])
async def feed(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    conn: asyncpg.Connection = Depends(get_conn),
):
    return rows(await articles_repo.list_feed(conn, limit, offset))


@router.get("/{article_id}", response_model=ArticleFeedOut)
async def get_article(article_id: UUID, conn: asyncpg.Connection = Depends(get_conn)):
    return require(await articles_repo.get_feed_one(conn, article_id), "Article not found")


@router.patch("/{article_id}", response_model=ArticleFeedOut)
async def update_article(
    article_id: UUID,
    body: ArticleUpdate,
    conn: asyncpg.Connection = Depends(get_conn),
    me: asyncpg.Record = Depends(current_user),
):
    updated = await articles_repo.update(conn, article_id, me["id"], body.model_dump(exclude_unset=True))
    if updated is None:
        if await articles_repo.get_feed_one(conn, article_id) is not None:
            raise DomainError(403, "Not the author of this article")
        raise DomainError(404, "Article not found")
    return dict(updated)


@router.delete("/{article_id}", status_code=204)
async def delete_article(
    article_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
    me: asyncpg.Record = Depends(current_user),
):
    if not await articles_repo.delete(conn, article_id, me["id"]):
        if await articles_repo.get_feed_one(conn, article_id) is not None:
            raise DomainError(403, "Not the author of this article")
        raise DomainError(404, "Article not found")
    return Response(status_code=204)
