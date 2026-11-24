from __future__ import annotations

"""Drop and recreate the case store, then re-seed the demo data.

PARAKH creates its schema with ``create_all`` (DECISIONS.md ADR-003; Alembic
arrives in Phase F), so a column added in a later phase never reaches an
existing SQLite file. Phase B added ``identifiers.role`` and Phase C adds the
units, user and audit tables, so a database created before them must be reset
rather than left to fail at query time.

Usage::

    python scripts/reset_demo_db.py            # ask before dropping
    python scripts/reset_demo_db.py --yes      # no prompt (CI, demo reset)
    python scripts/reset_demo_db.py --no-seed  # empty database, schema only
"""

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402
from app.db.models import Base  # noqa: E402
from app.db.session import build_database  # noqa: E402


def sqlite_path(url: str) -> Path | None:
    marker = "sqlite+aiosqlite:///"
    if not url.startswith(marker):
        return None
    raw = url[len(marker):]
    path = Path(raw)
    return path if path.is_absolute() else (ROOT / raw.lstrip("./")).resolve()


async def reset(seed: bool) -> int:
    settings = get_settings()
    database = build_database(settings)
    async with database.engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
    await database.create_all()
    print("schema dropped and recreated")
    await database.close()

    if seed:
        from app.db.demo_seed import seed_demo

        counts = await seed_demo(reset=False)
        print("seeded: " + ", ".join(f"{key}={value}" for key, value in sorted(counts.items())))
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    parser.add_argument("--no-seed", action="store_true", help="leave the database empty")
    args = parser.parse_args(argv)

    settings = get_settings()
    target = sqlite_path(settings.database_url)
    where = str(target) if target else settings.database_url.rpartition("@")[2]
    print(f"This deletes every case, identifier and audit row in: {where}")
    if not args.yes:
        try:
            answer = input("Type 'reset' to continue: ").strip().lower()
        except EOFError:
            print("cancelled (no terminal); pass --yes to run unattended")
            return 1
        if answer != "reset":
            print("cancelled")
            return 1
    return asyncio.run(reset(seed=not args.no_seed))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
