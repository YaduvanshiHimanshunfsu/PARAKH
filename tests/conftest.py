from __future__ import annotations

"""Shared test setup.

Every test gets its own throwaway SQLite file. Without this, any test that
builds the app from default settings opens the developer's real
``parakh_cases.db``: results depend on whatever is in it, one test can see
another's cases, and a schema change in a new phase makes unrelated tests fail
against a stale file.
"""

import os
import tempfile
from pathlib import Path

import pytest

_TEMP_ROOT = Path(tempfile.gettempdir()) / "parakh-tests"


@pytest.fixture(autouse=True, scope="session")
def isolated_database() -> None:
    """Point default settings at a per-run database, not the developer's."""

    _TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    path = _TEMP_ROOT / f"cases_{os.getpid()}.db"
    if path.exists():
        path.unlink()
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{path.as_posix()}"

    # Settings are cached, so clear the cache after changing the environment.
    from app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
    if previous is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = previous
