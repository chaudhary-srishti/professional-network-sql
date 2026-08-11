"""Data-access layer: one module per aggregate, raw parameterized SQL only.

Column names passed to `build_set_clause` come from Pydantic model fields (a fixed whitelist),
never from arbitrary client input, so composing them into the SET clause is safe. All *values*
are bound as `$n` parameters.
"""
from __future__ import annotations

from typing import Any


def build_set_clause(fields: dict[str, Any], start: int = 1) -> tuple[str, list[Any], int]:
    """Build a dynamic ``col = $n`` SET clause for a PATCH-style update.

    Returns (clause_sql, values, next_param_index).
    """
    cols: list[str] = []
    vals: list[Any] = []
    i = start
    for key, value in fields.items():
        cols.append(f"{key} = ${i}")
        vals.append(value)
        i += 1
    return ", ".join(cols), vals, i
