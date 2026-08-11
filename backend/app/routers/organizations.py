"""organizations routes (incl. membership and firm-scoped reads)."""
from __future__ import annotations

from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, Query, Response

from ..db import get_conn
from ..errors import DomainError
from ..repositories import links as links_repo
from ..repositories import organizations as orgs_repo
from ..repositories import posts as posts_repo
from ..schemas import (
    FirmStatsOut,
    FollowOut,
    MemberAdd,
    MemberOut,
    OrganizationCreate,
    OrganizationOut,
    OrganizationUpdate,
    PostFeedOut,
)
from ..security import current_user
from . import require, rows

router = APIRouter(prefix="/organizations", tags=["organizations"])


async def _require_owner(conn: asyncpg.Connection, org_id: UUID, me: asyncpg.Record) -> None:
    if me["super_admin"]:
        return
    is_owner = await conn.fetchval(
        "SELECT true FROM organization_members "
        "WHERE organization_id = $1 AND user_id = $2 AND role = 'owner'",
        org_id, me["id"],
    )
    if not is_owner:
        raise DomainError(403, "Requires firm owner")


@router.post("", response_model=OrganizationOut, status_code=201)
async def create_org(
    body: OrganizationCreate,
    conn: asyncpg.Connection = Depends(get_conn),
    me: asyncpg.Record = Depends(current_user),
):
    """Create a firm; the creator is recorded as its first 'owner' member (one transaction)."""
    data = body.model_dump(exclude_unset=True)
    async with conn.transaction():
        org = await orgs_repo.create(conn, data)
        await orgs_repo.add_member(conn, org["id"], me["id"], "owner")
    return dict(org)


@router.get("", response_model=list[OrganizationOut])
async def list_orgs(
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    conn: asyncpg.Connection = Depends(get_conn),
):
    return rows(await orgs_repo.search(conn, q, category, limit, offset))


@router.get("/{org_id}", response_model=OrganizationOut)
async def get_org(org_id: UUID, conn: asyncpg.Connection = Depends(get_conn)):
    return require(await orgs_repo.get(conn, org_id), "Organization not found")


@router.patch("/{org_id}", response_model=OrganizationOut)
async def update_org(
    org_id: UUID,
    body: OrganizationUpdate,
    conn: asyncpg.Connection = Depends(get_conn),
    me: asyncpg.Record = Depends(current_user),
):
    await _require_owner(conn, org_id, me)
    return require(
        await orgs_repo.update(conn, org_id, body.model_dump(exclude_unset=True)),
        "Organization not found",
    )


@router.delete("/{org_id}", status_code=204)
async def delete_org(
    org_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
    me: asyncpg.Record = Depends(current_user),
):
    await _require_owner(conn, org_id, me)
    if not await orgs_repo.delete(conn, org_id):
        raise DomainError(404, "Organization not found")
    return Response(status_code=204)


@router.get("/{org_id}/stats", response_model=FirmStatsOut)
async def org_stats(org_id: UUID, conn: asyncpg.Connection = Depends(get_conn)):
    return require(await orgs_repo.stats(conn, org_id), "Organization not found")


# --- members ---------------------------------------------------------------------------------
@router.get("/{org_id}/members", response_model=list[MemberOut])
async def list_members(org_id: UUID, conn: asyncpg.Connection = Depends(get_conn)):
    return rows(await orgs_repo.list_members(conn, org_id))


@router.post("/{org_id}/members", response_model=MemberOut, status_code=201)
async def add_member(
    org_id: UUID,
    body: MemberAdd,
    conn: asyncpg.Connection = Depends(get_conn),
    me: asyncpg.Record = Depends(current_user),
):
    await _require_owner(conn, org_id, me)
    return dict(await orgs_repo.add_member(conn, org_id, body.user_id, body.role))


@router.delete("/{org_id}/members/{user_id}", status_code=204)
async def remove_member(
    org_id: UUID,
    user_id: UUID,
    conn: asyncpg.Connection = Depends(get_conn),
    me: asyncpg.Record = Depends(current_user),
):
    await _require_owner(conn, org_id, me)
    if not await orgs_repo.remove_member(conn, org_id, user_id):
        raise DomainError(404, "Membership not found")
    return Response(status_code=204)


# --- firm-scoped reads -----------------------------------------------------------------------
@router.get("/{org_id}/followers", response_model=list[FollowOut])
async def org_followers(org_id: UUID, conn: asyncpg.Connection = Depends(get_conn)):
    return rows(await links_repo.list_followers(conn, org_id))


@router.get("/{org_id}/posts", response_model=list[PostFeedOut])
async def org_posts(
    org_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    conn: asyncpg.Connection = Depends(get_conn),
):
    return rows(await posts_repo.list_by_firm(conn, org_id, limit, offset))
