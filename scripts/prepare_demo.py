from __future__ import annotations

"""Make the database usable, then seed what is missing.

``run.py`` calls this before starting the servers so that one command gets the
whole project running. It is written to be safe to run repeatedly.

What it does, in order:

1. Create any missing tables.
2. Check the schema against the models. If a column is missing - a database
   from an earlier phase - the file is **moved aside with a timestamp**, not
   deleted, and a fresh one is created. The path of the backup is printed, so
   nothing is irrecoverable.
3. Seed the unit hierarchy and the demo officer accounts if they are absent.
4. Seed the demo cases, but only when the case store is empty, so a second run
   does not duplicate them or spend a minute re-analysing.

Usage::

    python scripts/prepare_demo.py                 # heal + seed what is missing
    python scripts/prepare_demo.py --reset         # start from an empty database
    python scripts/prepare_demo.py --no-demo-cases # hierarchy and officers only
"""

import argparse
import asyncio
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402
from app.db.models import CaseRecord, UserRecord  # noqa: E402
from app.db.schema_check import describe, verify_schema  # noqa: E402
from app.db.session import build_database  # noqa: E402
from app.db.units_seed import DEMO_USERS, seed_hierarchy  # noqa: E402

DEMO_PASSWORD = "ParakhDemo@2026"
SQLITE_PREFIX = "sqlite+aiosqlite:///"


def sqlite_path(url: str) -> Path | None:
    """The file a SQLite URL points at, or None for another database."""

    if not url.startswith(SQLITE_PREFIX) or ":memory:" in url:
        return None
    raw = url[len(SQLITE_PREFIX):]
    path = Path(raw)
    return path if path.is_absolute() else (ROOT / raw.lstrip("./")).resolve()


def move_aside(path: Path) -> Path:
    """Rename a database file out of the way, keeping it recoverable."""

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"{path.stem}.backup-{stamp}{path.suffix}")
    shutil.move(str(path), str(backup))
    for suffix in ("-wal", "-shm", "-journal"):
        extra = Path(str(path) + suffix)
        if extra.exists():
            extra.unlink()
    return backup


async def _counts(database) -> tuple[int, int]:
    from sqlalchemy import func, select

    async with database.session() as session:
        users = (await session.execute(select(func.count(UserRecord.id)))).scalar_one()
        cases = (await session.execute(select(func.count(CaseRecord.id)))).scalar_one()
    return users, cases


async def prepare(*, reset: bool, demo_cases: bool, password: str) -> int:
    settings = get_settings()
    target = sqlite_path(settings.database_url)

    if reset and target is not None and target.exists():
        backup = move_aside(target)
        print(f"[prepare] existing database moved to {backup.name}")

    database = build_database(settings)
    await database.create_all()

    drift = None
    try:
        drift = await verify_schema(database.engine, strict=False)
    finally:
        pass

    if drift and "is missing:" in (drift or ""):
        await database.close()
        if target is None:
            print(
                "[prepare] The database schema is out of date and it is not a local SQLite "
                f"file, so this script will not touch it.\n[prepare] {describe([], {})}{drift}\n"
                "[prepare] Apply the change with your own migration process."
            )
            return 1
        backup = move_aside(target)
        print(
            "[prepare] This database was created by an earlier version of PARAKH "
            f"({drift}).\n"
            f"[prepare] It has been moved to {backup.name} and a fresh one created. "
            "Nothing was deleted."
        )
        database = build_database(settings)
        await database.create_all()

    os.environ.setdefault("DEMO_OFFICER_PASSWORD", password)
    async with database.session() as session:
        counts = await seed_hierarchy(session)
    if counts["users"]:
        print(f"[prepare] created {counts['users']} demo officer accounts")

    users, cases = await _counts(database)
    await database.close()

    if demo_cases and cases == 0:
        print("[prepare] seeding demo cases (first run; this takes a moment)...")
        from app.db.demo_seed import seed_demo

        seeded = await seed_demo(reset=False)
        print("[prepare] demo cases: " + ", ".join(f"{k}={v}" for k, v in sorted(seeded.items())))
    elif cases:
        print(f"[prepare] {cases} cases already present; not reseeding")

    print(f"[prepare] ready: {users} officer accounts, {max(cases, 0)} cases")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="move the current database aside and start empty")
    parser.add_argument("--no-demo-cases", action="store_true", help="hierarchy and officers only")
    parser.add_argument("--password", default=DEMO_PASSWORD, help="password for the demo accounts")
    args = parser.parse_args(argv)
    return asyncio.run(
        prepare(reset=args.reset, demo_cases=not args.no_demo_cases, password=args.password)
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
