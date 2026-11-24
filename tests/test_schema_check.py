from __future__ import annotations

"""Startup schema check.

PARAKH creates its schema with ``create_all``, which adds new tables but never
adds a column to a table that already exists. A database file from an earlier
phase therefore starts fine and then fails deep inside a query with
``no such column: users.display_name`` - a message that tells the operator
nothing. These tests pin the clear failure instead.
"""

import asyncio

import pytest
from sqlalchemy import text

from app.db.models import Base
from app.db.schema_check import RESET_COMMAND, SchemaOutOfDateError, describe, verify_schema
from app.db.session import Database


def run(coroutine):
    return asyncio.run(coroutine)


def test_a_current_schema_reports_no_drift():
    async def case():
        database = Database("sqlite+aiosqlite:///:memory:")
        await database.create_all()
        try:
            return await verify_schema(database.engine)
        finally:
            await database.close()

    assert run(case()) is None


def test_a_missing_column_fails_with_an_instruction():
    async def case():
        database = Database("sqlite+aiosqlite:///:memory:")
        await database.create_all()
        # Recreate "users" as it looked before Phase C added rank and unit.
        async with database.engine.begin() as connection:
            await connection.execute(text("DROP TABLE users"))
            await connection.execute(
                text(
                    "CREATE TABLE users ("
                    " id INTEGER PRIMARY KEY,"
                    " username VARCHAR(64),"
                    " password_hash VARCHAR(256),"
                    " role VARCHAR(16),"
                    " is_active BOOLEAN,"
                    " created_at DATETIME)"
                )
            )
        try:
            await verify_schema(database.engine)
        finally:
            await database.close()

    with pytest.raises(SchemaOutOfDateError) as error:
        run(case())

    message = str(error.value)
    # The operator needs to know which columns, and exactly what to run.
    assert "display_name" in message
    assert "rank" in message
    assert RESET_COMMAND in message
    assert "deletes every case" in message


def test_a_missing_table_is_a_warning_not_a_failure():
    """A new table is added by create_all, so its absence is not fatal."""

    async def case():
        database = Database("sqlite+aiosqlite:///:memory:")
        await database.create_all()
        async with database.engine.begin() as connection:
            await connection.execute(text("DROP TABLE documents"))
        try:
            return await verify_schema(database.engine, strict=False)
        finally:
            await database.close()

    detail = run(case())
    assert detail is not None and "documents" in detail


def test_describe_lists_tables_and_columns():
    text_out = describe(["documents"], {"users": ["rank", "unit_id"]})
    assert "missing tables: documents" in text_out
    assert "users is missing: rank, unit_id" in text_out


def test_every_model_table_is_checked():
    """The check must cover the whole metadata, not a hardcoded list."""

    async def case():
        database = Database("sqlite+aiosqlite:///:memory:")
        await database.create_all()
        async with database.engine.begin() as connection:
            for table in ("documents", "approvals", "audit_events", "units"):
                await connection.execute(text(f"DROP TABLE {table}"))
        try:
            return await verify_schema(database.engine, strict=False)
        finally:
            await database.close()

    detail = run(case())
    for table in ("documents", "approvals", "audit_events", "units"):
        assert table in detail
    assert set(Base.metadata.tables) >= {"documents", "approvals", "audit_events", "units"}
