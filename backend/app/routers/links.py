"""Social-graph routes: connections, follows, member requests. Actor is always current_user."""
from __future__ import annotations

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, Query, Response

from ..db import get_conn
from ..errors import DomainError
from ..repositories import links as links_repo
from ..schemas import (
    ConnectionCreate,
    ConnectionEdgeOut,
    ConnectionOut,
    FollowCreate,
    FollowOut,
    MemberRequestCreate,
    MemberRequestOut,
)
from ..security import current_user
from . import require, rows

router = APIRouter(tags=["links"])


# --- connections -----------------------------------------------------------------------------
@router.post("/connections", response_model=ConnectionOut, status_code=201)
async def create_connection(
    body: ConnectionCreate,
    conn: asyncpg.Connection = Depends(get_conn),
    me: asyncpg.Record = Depends(current_user),
):
    if body.target_id == me["id"]:
        raise DomainError(422, "Cannot connect to yourself")
    return dict(await links_repo.create_connection(conn, me["id"], body.target_id, body.personal_note))


@router.get("/connections", response_model=list[ConnectionEdgeOut])
async def my_connections(
    status: str | None = Query(default=None, description="pending|accepted|rejected"),
    conn: asyncpg.Connection = Depends(get_conn),
    me: asyncpg.Record = Depends(current_user),
):
    return rows(await links_repo.list_edges(conn, me["id"], status))


@router.post("/connections/{connection_id}/accept", response_model=ConnectionOut)
async def accept_connection(
    connection_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
    me: asyncpg.Record = Depends(current_user),
):
    return require(
        await links_repo.respond_connection(conn, connection_id, me["id"], "accepted"),
        "No pending request addressed to you with that id", status=403,
    )


@router.post("/connections/{connection_id}/reject", response_model=ConnectionOut)
async def reject_connection(
    connection_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
    me: asyncpg.Record = Depends(current_user),
):
    return require(
        await links_repo.respond_connection(conn, connection_id, me["id"], "rejected"),
        "No pending request addressed to you with that id", status=403,
    )


@router.delete("/connections/{connection_id}", status_code=204)
async def delete_connection(
    connection_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
    me: asyncpg.Record = Depends(current_user),
):
    if not await links_repo.delete_connection(conn, connection_id, me["id"]):
        raise DomainError(404, "Connection not found or not yours")
    return Response(status_code=204)


# --- follows ---------------------------------------------------------------------------------
@router.post("/follows", response_model=FollowOut, status_code=201)
async def follow(
    body: FollowCreate,
    conn: asyncpg.Connection = Depends(get_conn),
    me: asyncpg.Record = Depends(current_user),
):
    return dict(await links_repo.follow(conn, me["id"], body.organization_id))


@router.get("/follows", response_model=list[FollowOut])
async def my_following(
    conn: asyncpg.Connection = Depends(get_conn),
    me: asyncpg.Record = Depends(current_user),
):
    return rows(await links_repo.list_following(conn, me["id"]))


@router.delete("/follows/{org_id}", status_code=204)
async def unfollow(
    org_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
    me: asyncpg.Record = Depends(current_user),
):
    if not await links_repo.unfollow(conn, me["id"], org_id):
        raise DomainError(404, "Not following that organization")
    return Response(status_code=204)


# --- firm member requests --------------------------------------------------------------------
@router.post("/member-requests", response_model=MemberRequestOut, status_code=201)
async def create_member_request(
    body: MemberRequestCreate,
    conn: asyncpg.Connection = Depends(get_conn),
    me: asyncpg.Record = Depends(current_user),
):
    return dict(await links_repo.create_member_request(conn, me["id"], body.organization_id, body.personal_note))


@router.post("/member-requests/{request_id}/accept", response_model=MemberRequestOut)
async def accept_member_request(
    request_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
    me: asyncpg.Record = Depends(current_user),
):
    return require(
        await links_repo.respond_member_request(conn, request_id, me["id"], "accepted"),
        "No pending request you may act on with that id", status=403,
    )


@router.post("/member-requests/{request_id}/reject", response_model=MemberRequestOut)
async def reject_member_request(
    request_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
    me: asyncpg.Record = Depends(current_user),
):
    return require(
        await links_repo.respond_member_request(conn, request_id, me["id"], "rejected"),
        "No pending request you may act on with that id", status=403,
    )
