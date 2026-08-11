"""Translate database-level failures into clean HTTP responses.

The schema enforces a lot of invariants (unique keys, CHECKs, FKs, the email-immutability
trigger). Rather than pre-checking each in Python — which would reintroduce the check-then-act
races the relational design removed — we let the database raise and map the SQLSTATE here.
"""
from __future__ import annotations

import asyncpg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# SQLSTATE -> (HTTP status, public message)
_SQLSTATE_MAP: dict[str, tuple[int, str]] = {
    "23505": (409, "Resource already exists"),        # unique_violation
    "23503": (409, "Referenced resource missing or still in use"),  # foreign_key_violation
    "23514": (422, "Value violates a constraint"),    # check_violation
    "23502": (422, "Missing required field"),         # not_null_violation
    "22P02": (422, "Malformed value (e.g. invalid UUID)"),  # invalid_text_representation
    "P0001": (400, "Operation not allowed"),          # raise_exception (e.g. email immutable)
}


class DomainError(Exception):
    """Raised by repositories/routers for app-level rejections (auth, ownership, not found)."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(asyncpg.PostgresError)
    async def _pg_error(_: Request, exc: asyncpg.PostgresError) -> JSONResponse:
        sqlstate = getattr(exc, "sqlstate", None)
        status, message = _SQLSTATE_MAP.get(sqlstate, (400, "Database error"))
        detail = message
        # The email-immutability trigger carries a useful, safe message — surface it.
        if sqlstate == "P0001" and getattr(exc, "message", None):
            detail = exc.message
        return JSONResponse(status_code=status, content={"detail": detail})
