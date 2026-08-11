"""Professional Network SQL backend — FastAPI over the relational schema (raw asyncpg, no ORM).

The app assumes the schema already exists (created via the project's `make migrate`); it
contains no migration or DDL logic — it only reads and writes rows.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db import close_pool, create_pool
from .errors import register_error_handlers
from .routers import articles, engagement, links, organizations, posts, users


@asynccontextmanager
async def lifespan(_: FastAPI):
    await create_pool()
    try:
        yield
    finally:
        await close_pool()


app = FastAPI(
    title="Professional Network — SQL Backend",
    version="0.1.0",
    summary="CRUD + domain actions over the professional-network relational schema.",
    lifespan=lifespan,
)

register_error_handlers(app)

for module in (users, organizations, links, posts, articles, engagement):
    app.include_router(module.router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
