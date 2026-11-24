from __future__ import annotations

"""Create the demo police hierarchy and its officer accounts.

These are **demonstration accounts for the hackathon build only.** The
password is the same for every account so a judge can switch roles quickly,
and it is printed on screen rather than hidden. That is a deliberate
trade-off for a demo and is exactly what must not happen in a deployment:

* a real deployment creates accounts through the admin role, one password
  each, set by the officer at first sign-in;
* PARAKH stores only a hash, so even here the password is never written to
  the database in clear;
* the lockout, MFA and audit controls from Phase C apply to these accounts
  just as they would to real ones.

Usage::

    python scripts/seed_demo_officers.py                 # default demo password
    python scripts/seed_demo_officers.py --password ...  # choose your own
    python scripts/seed_demo_officers.py --show          # list accounts only
"""

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402
from app.db.session import build_database  # noqa: E402
from app.db.units_seed import DEMO_USERS, UNITS, seed_hierarchy  # noqa: E402

# Documented demo password. Long enough to pass the policy, obviously not a
# secret, and never used outside this script.
DEMO_PASSWORD = "ParakhDemo@2026"

ROLE_SUMMARY = {
    "SUPERVISOR": "District supervisor - sees the whole district, gives final approval on freezes and takedowns",
    "STATION_HEAD": "SHO - sees the station, assigns cases, gives station-level approval",
    "IO": "Investigating officer - works assigned cases, drafts requisitions",
    "OPERATOR": "Operator - submits items for analysis, sees only their own submissions",
    "STATE_VIEWER": "State cyber cell - read-only across the state",
}


async def _enrolled_secrets(session) -> dict[str, str]:
    """TOTP secrets just created, so a judge can add them to an app."""

    from sqlalchemy import select

    from app.db.models import UserRecord

    rows = (await session.execute(select(UserRecord).where(UserRecord.totp_secret.is_not(None)))).scalars()
    return {row.username: row.totp_secret for row in rows}


def print_accounts(password: str) -> None:
    width = max(len(name) for name, *_ in DEMO_USERS) + 2
    print("\nDemo accounts (all share the same password for the demo):\n")
    print(f"  {'username'.ljust(width)} {'rank'.ljust(10)} {'role'.ljust(13)} unit")
    print(f"  {'-' * width} {'-' * 10} {'-' * 13} {'-' * 14}")
    for username, _display, rank, role, unit_code, mfa in DEMO_USERS:
        flag = "  (MFA when --mfa is used)" if mfa else ""
        print(f"  {username.ljust(width)} {rank.ljust(10)} {role.ljust(13)} {unit_code}{flag}")
    print(f"\n  password for every account: {password}\n")
    print("  What each role may do:")
    for role, text in ROLE_SUMMARY.items():
        print(f"    {role.ljust(13)} {text}")
    print("\n  Chain of command for a freeze request (BNSS s.106):")
    print("    io.sharma drafts  ->  sho.cyber approves (station)  ->  sp.jaipur approves (district)")
    print("    ->  dispatch recorded  ->  bank's reply recorded against the case\n")
    print("  Jurisdiction: io.btp is in Bharatpur and cannot see Jaipur's cases at all.\n")


async def seed(password: str, enrol_mfa: bool) -> int:
    import os

    os.environ["DEMO_OFFICER_PASSWORD"] = password
    settings = get_settings()
    database = build_database(settings)
    await database.create_all()
    async with database.session() as session:
        counts = await seed_hierarchy(session, enrol_mfa=enrol_mfa)
        secrets = await _enrolled_secrets(session) if enrol_mfa else {}
    await database.close()
    print(f"units: {counts['units']} present, officers created: {counts['users']}")
    for username, secret in secrets.items():
        print(f"  MFA secret for {username}: {secret}  (add to an authenticator app)")
    if counts["users"] == 0:
        print("(accounts already existed; no passwords were changed)")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--password", default=DEMO_PASSWORD, help="password for every demo account")
    parser.add_argument("--show", action="store_true", help="only print the accounts, change nothing")
    parser.add_argument(
        "--mfa",
        action="store_true",
        help="enrol TOTP for supervisor accounts (needs an authenticator app to sign in)",
    )
    args = parser.parse_args(argv)

    if len(args.password) < 12:
        print("Password must be at least 12 characters.")
        return 1

    print(f"Units in the demo hierarchy: {len(UNITS)}")
    if args.show:
        print_accounts(args.password)
        return 0

    result = asyncio.run(seed(args.password, args.mfa))
    print_accounts(args.password)
    print("These are demonstration accounts. Do not use this password in a real deployment.")
    return result


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
