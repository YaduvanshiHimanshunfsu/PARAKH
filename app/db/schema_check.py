from __future__ import annotations

"""Detect a database created by an older version of PARAKH.

``create_all`` creates missing *tables*, but it never adds a *column* to a
table that already exists. So a database file created before Phase C added
``users.rank`` or Phase D added the ``documents`` table keeps working right up
until the first query touches the new column, and then fails deep inside
SQLAlchemy with ``no such column: users.display_name``.

That stack trace tells a user nothing about what to do. This check runs at
startup, compares what the model expects with what the file actually has, and
fails with an instruction instead.

Alembic migrations arrive in Phase F (DECISIONS.md ADR-003). Until then the
answer for a development or demo database is to recreate it.
"""

import logging

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.models import Base

logger = logging.getLogger(__name__)

RESET_COMMAND = "python scripts/reset_demo_db.py --yes"


class SchemaOutOfDateError(RuntimeError):
    """The database file predates the current model definitions."""


def _differences(connection) -> tuple[list[str], dict[str, list[str]]]:
    """Return (missing tables, {table: [missing columns]})."""

    inspector = inspect(connection)
    present_tables = set(inspector.get_table_names())

    missing_tables: list[str] = []
    missing_columns: dict[str, list[str]] = {}

    for name, table in Base.metadata.tables.items():
        if name not in present_tables:
            missing_tables.append(name)
            continue
        actual = {column["name"] for column in inspector.get_columns(name)}
        absent = [column.name for column in table.columns if column.name not in actual]
        if absent:
            missing_columns[name] = absent

    return missing_tables, missing_columns


def describe(missing_tables: list[str], missing_columns: dict[str, list[str]]) -> str:
    parts: list[str] = []
    if missing_tables:
        parts.append("missing tables: " + ", ".join(sorted(missing_tables)))
    for table, columns in sorted(missing_columns.items()):
        parts.append(f"{table} is missing: {', '.join(sorted(columns))}")
    return "; ".join(parts)


async def verify_schema(engine: AsyncEngine, *, strict: bool = True) -> str | None:
    """Check the live schema against the models.

    Returns a description of the drift, or ``None`` when the schema matches.
    Raises :class:`SchemaOutOfDateError` when ``strict`` and columns are
    missing, because every query against that table would fail anyway.
    """

    async with engine.begin() as connection:
        missing_tables, missing_columns = await connection.run_sync(
            lambda sync_connection: _differences(sync_connection)
        )

    if not missing_tables and not missing_columns:
        return None

    detail = describe(missing_tables, missing_columns)
    if missing_columns and strict:
        raise SchemaOutOfDateError(
            "This database was created by an older version of PARAKH and is missing "
            f"columns the application needs ({detail}).\n\n"
            "PARAKH creates its schema with create_all, which adds new tables but cannot "
            "add a column to a table that already exists (Alembic migrations arrive in "
            "Phase F).\n\n"
            f"To recreate the database and reload the demo data, run:\n    {RESET_COMMAND}\n\n"
            "That deletes every case, identifier and audit row in the current database."
        )

    logger.warning("schema_drift detail=%s", detail)
    return detail


__all__ = ["RESET_COMMAND", "SchemaOutOfDateError", "describe", "verify_schema"]
