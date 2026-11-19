from __future__ import annotations

"""Load reviewed blacklist entries into the case store.

Run directly to populate a fresh database:

    python -m app.db.seed

Idempotent: existing entries are left untouched, so it is safe to re-run before
a demo. Demo *cases* are seeded separately in Phase 7.3 — an empty dashboard
demos badly, but case seeding should not happen implicitly at startup.
"""

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.data.blacklists import SEED_BLACKLIST
from app.db.models import BlacklistEntry
from app.db.session import build_database

logger = logging.getLogger(__name__)


async def seed_blacklist(session: AsyncSession) -> int:
    """Insert any missing blacklist entries. Returns the number added."""

    existing = {
        (row.type, row.value)
        for row in (await session.execute(select(BlacklistEntry))).scalars().all()
    }
    added = 0
    for entry in SEED_BLACKLIST:
        if (entry.type.value, entry.value) in existing:
            continue
        session.add(
            BlacklistEntry(
                type=entry.type.value,
                value=entry.value,
                source=entry.source,
                reason=entry.reason,
            )
        )
        added += 1
    await session.flush()
    return added


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = get_settings()
    database = build_database(settings)
    await database.create_all()
    async with database.session() as session:
        added = await seed_blacklist(session)
    await database.close()
    logger.info("blacklist_seeded added=%d total_seeds=%d", added, len(SEED_BLACKLIST))


if __name__ == "__main__":
    asyncio.run(main())
