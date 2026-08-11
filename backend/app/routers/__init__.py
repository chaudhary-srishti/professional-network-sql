"""Router helpers."""
from __future__ import annotations

from typing import Any

import asyncpg

from ..errors import DomainError


def require(record: asyncpg.Record | None, detail: str = "Not found", status: int = 404) -> dict[str, Any]:
    """Return the record as a dict, or raise a DomainError if it is None."""
    if record is None:
        raise DomainError(status, detail)
    return dict(record)


def rows(records: list[asyncpg.Record]) -> list[dict[str, Any]]:
    return [dict(r) for r in records]
