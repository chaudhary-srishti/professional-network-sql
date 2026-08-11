"""Test harness.

Uses a dedicated `professional_network_test` database so the suite never touches dev data. The database is
created (if missing) and its schema is rebuilt from the project's own migration files at session
start; every test starts from a truncated schema.
"""
from __future__ import annotations

import asyncio
import os
import pathlib

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

TEST_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://professional_network:professional_network@localhost:5433/professional_network_test",
)
ADMIN_URL = os.environ.get(
    "ADMIN_DATABASE_URL",
    "postgresql://professional_network:professional_network@localhost:5433/postgres",
)

# Point the app at the test DB *before* importing it.
os.environ["DATABASE_URL"] = TEST_URL

from app import db as db_module  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.main import app  # noqa: E402

get_settings.cache_clear()

_MIGRATIONS = sorted(
    p for p in (pathlib.Path(__file__).resolve().parents[2] / "database" / "migrations").glob("0*.sql")
    if "optional" not in p.name
)

_TABLES = (
    "users, organizations, organization_members, user_connections, organization_follows, "
    "firm_member_requests, posts, articles, comments, likes"
)


async def _create_test_db() -> None:
    admin = await asyncpg.connect(ADMIN_URL)
    try:
        await admin.execute("CREATE DATABASE professional_network_test")
    except asyncpg.DuplicateDatabaseError:
        pass
    finally:
        await admin.close()


async def _apply_schema() -> None:
    conn = await asyncpg.connect(TEST_URL)
    try:
        await conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        for migration in _MIGRATIONS:
            await conn.execute(migration.read_text())
    finally:
        await conn.close()


@pytest.fixture(scope="session", autouse=True)
def _schema() -> None:
    asyncio.run(_create_test_db())
    asyncio.run(_apply_schema())
    yield


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    await db_module.create_pool()
    # Clean slate for each test.
    conn = await asyncpg.connect(TEST_URL)
    await conn.execute(f"TRUNCATE {_TABLES} RESTART IDENTITY CASCADE")
    await conn.close()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await db_module.close_pool()


async def make_user(client: AsyncClient, email: str, name: str) -> dict:
    resp = await client.post("/users", json={"email": email, "name": name})
    assert resp.status_code == 201, resp.text
    return resp.json()


def auth(email: str) -> dict:
    return {"X-User-Email": email}
