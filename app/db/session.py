from __future__ import annotations

"""Async engine and session management for the investigation case store."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Request
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings
from app.db.models import Base

logger = logging.getLogger(__name__)


def _enable_sqlite_foreign_keys(engine: AsyncEngine) -> None:
    """Turn on foreign-key enforcement for every SQLite connection.

    SQLite ignores foreign keys unless this pragma is set per connection, which
    makes every ``ondelete="CASCADE"`` in the models silently inert. Without it,
    deleting a case leaves its findings and identifiers behind as orphans that
    still appear in the heat-list and can collide with a reused row id.
    """

    @event.listens_for(engine.sync_engine, "connect")
    def _set_pragma(dbapi_connection, _record) -> None:  # pragma: no cover - driver hook
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()


class Database:
    """Owns the engine and session factory for one application instance."""

    def __init__(self, url: str, echo: bool = False) -> None:
        self._url = url
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        self._engine: AsyncEngine = create_async_engine(
            url,
            echo=echo,
            future=True,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        self._sessionmaker = async_sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )
        if url.startswith("sqlite"):
            _enable_sqlite_foreign_keys(self._engine)

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    async def create_all(self) -> None:
        """Create tables if absent.

        Deliberately no Alembic: a 24-hour build does not benefit from migration
        tooling, and the schema is recreated from scratch between demos.
        """

        async with self._engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        logger.info("investigation_store_ready url=%s", self._redacted_url())

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Transactional scope: commits on success, rolls back on any exception."""

        async with self._sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    def _redacted_url(self) -> str:
        if "@" in self._url:
            scheme, _, tail = self._url.partition("://")
            return f"{scheme}://***@{tail.rpartition('@')[2]}"
        return self._url

    async def close(self) -> None:
        await self._engine.dispose()


def build_database(settings: Settings) -> Database:
    return Database(settings.database_url, echo=settings.db_echo)


def get_database(request: Request) -> Database:
    """FastAPI dependency returning the app-scoped Database.

    The ``Request`` annotation is required: without it FastAPI reads ``request``
    as a query parameter instead of injecting the request object.
    """

    return request.app.state.database


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding one transactional session per request."""

    database: Database = request.app.state.database
    async with database.session() as session:
        yield session
