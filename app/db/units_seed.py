from __future__ import annotations

"""Unit hierarchy and role accounts for the demo (planversionalpha.md C.6).

The structure mirrors how Rajasthan Police is actually organised: State HQ ->
Range (IG) -> District (SP) or Commissionerate -> Police Station (SHO), with
district cyber police stations. Two districts are seeded so jurisdiction
scoping is visible: an officer in Bharatpur must not see Jaipur's cases.

The usernames are **role labels, not real people**. Passwords come from the
environment; nothing is hard-coded here.
"""

import logging
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.db.models import UnitRecord, UserRecord

logger = logging.getLogger(__name__)

# code, name, type, parent code
UNITS: tuple[tuple[str, str, str, str | None], ...] = (
    ("RJ", "Rajasthan Police (State HQ)", "STATE", None),
    ("JPR-RANGE", "Jaipur Range", "RANGE", "RJ"),
    ("JPR-COMM", "Jaipur Commissionerate", "DISTRICT", "JPR-RANGE"),
    ("JPR-CYBER-PS", "Cyber Police Station, Jaipur", "STATION", "JPR-COMM"),
    ("JPR-SOUTH-PS", "Jaipur South Police Station", "STATION", "JPR-COMM"),
    ("BTP-RANGE", "Bharatpur Range", "RANGE", "RJ"),
    ("BTP-DISTRICT", "Bharatpur District", "DISTRICT", "BTP-RANGE"),
    ("BTP-CYBER-PS", "Cyber Police Station, Bharatpur", "STATION", "BTP-DISTRICT"),
)

# username, display name, rank, role, unit code, needs MFA
DEMO_USERS: tuple[tuple[str, str, str, str, str, bool], ...] = (
    ("sp.jaipur", "SP (Cyber), Jaipur", "SP", "SUPERVISOR", "JPR-COMM", True),
    ("dysp.cyber", "DySP, Cyber Cell", "DYSP", "SUPERVISOR", "JPR-COMM", False),
    ("sho.cyber", "SHO, Cyber PS Jaipur", "INSPECTOR", "STATION_HEAD", "JPR-CYBER-PS", False),
    ("io.si.sharma", "SI (Investigating Officer)", "SI", "IO", "JPR-CYBER-PS", False),
    ("op.hc", "Head Constable (Operator)", "HC", "OPERATOR", "JPR-CYBER-PS", False),
    ("io.btp", "Inspector, Cyber PS Bharatpur", "INSPECTOR", "IO", "BTP-CYBER-PS", False),
    ("viewer.state", "State Cyber Cell (read only)", "ADG", "STATE_VIEWER", "RJ", False),
)

DEMO_PASSWORD_ENV = "DEMO_OFFICER_PASSWORD"


async def seed_units(session: AsyncSession) -> dict[str, UnitRecord]:
    """Create the unit tree and return it by code. Idempotent."""

    existing = {
        unit.code: unit for unit in (await session.execute(select(UnitRecord))).scalars().all()
    }
    created: dict[str, UnitRecord] = dict(existing)
    for code, name, kind, parent_code in UNITS:
        if code in created:
            continue
        parent = created.get(parent_code) if parent_code else None
        unit = UnitRecord(
            code=code,
            name=name,
            type=kind,
            parent_id=parent.id if parent else None,
            # Materialised path: "everything under my unit" is one prefix match.
            path=f"{parent.path}{code}/" if parent else f"/{code}/",
        )
        session.add(unit)
        await session.flush()
        created[code] = unit
    return created


async def seed_users(session: AsyncSession, units: dict[str, UnitRecord]) -> int:
    """Create the demo role accounts. Returns how many were created.

    The password comes from ``DEMO_OFFICER_PASSWORD``; without it no demo
    account is created, so a deployment cannot accidentally ship with a known
    password baked into the source.
    """

    password = os.environ.get(DEMO_PASSWORD_ENV, "").strip()
    if not password:
        logger.warning("demo_users_skipped reason=%s_not_set", DEMO_PASSWORD_ENV)
        return 0
    if len(password) < 12:
        logger.warning("demo_users_skipped reason=password_too_short")
        return 0

    created = 0
    for username, display, rank, role, unit_code, needs_mfa in DEMO_USERS:
        exists = (
            await session.execute(select(UserRecord).where(UserRecord.username == username))
        ).scalar_one_or_none()
        if exists is not None:
            continue
        unit = units.get(unit_code)
        user = UserRecord(
            username=username,
            password_hash=hash_password(password),
            role=role,
            rank=rank,
            display_name=display,
            unit_id=unit.id if unit else None,
            is_active=True,
        )
        if needs_mfa:
            user.totp_secret = _new_totp_secret()
        session.add(user)
        created += 1
    await session.flush()
    return created


def _new_totp_secret() -> str | None:
    """A per-account TOTP secret, if pyotp is available."""

    try:
        import pyotp
    except ImportError:
        return None
    return pyotp.random_base32()


async def seed_hierarchy(session: AsyncSession) -> dict[str, int]:
    units = await seed_units(session)
    users = await seed_users(session, units)
    return {"units": len(units), "users": users}


__all__ = ["DEMO_USERS", "UNITS", "seed_hierarchy", "seed_units", "seed_users"]
