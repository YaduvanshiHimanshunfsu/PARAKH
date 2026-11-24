from __future__ import annotations

"""Populate the case store with a realistic, cross-linked demo dataset.

An empty investigation dashboard demonstrates nothing: search returns no rows,
the heat-list is blank, and linking has nothing to link. This seeds a coherent
scenario where identifiers are deliberately reused across artifact types, so
the linking, similarity and heat-list features have something real to show.

    python -m app.db.demo_seed            # add demo cases
    python -m app.db.demo_seed --reset    # delete existing cases first
    python -m app.db.demo_seed --export-apks samples   # write demo APKs to upload

Every value here is synthetic. Replace with the R4C sample dataset when it is
available, and never seed real personal data.
"""

import argparse
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete

from app.config import get_settings
from app.db.models import CaseRecord, FindingRecord, IdentifierRecord
from app.db.seed import seed_blacklist
from app.db.session import build_database
from app.schemas import ArtifactType, CaseSource, InputLanguage
from app.services.apk_analyzer import ApkAnalyzer
from app.services.artifact_analyzer import ArtifactAnalyzer
from app.services.case_service import create_case
from app.services.email_analyzer import EmailAnalyzer
from app.services.scam_analyzer import ScamAnalyzer
from app.services.url_enrichment import UrlEnrichmentService
from app.services.website_analyzer import WebsiteAnalyzer

logger = logging.getLogger(__name__)

# One campaign deliberately threads these through every artifact type, so the
# demo can show an APK, an SMS and a website converging on one operation.
CAMPAIGN_UPI = "richplan@ybl"
CAMPAIGN_PHONE = "9812345670"
CAMPAIGN_HOST = "45.133.1.9"
ROTATED_PHONE = "9123456780"

MESSAGES: tuple[tuple[str, int, str], ...] = (
    (
        "Ponzi recruitment SMS",
        21,
        f"RichPlan Investment: Guaranteed 10% daily returns! Referral bonus on every downline "
        f"member. Joining package Rs 5000. Pay {CAMPAIGN_UPI} or call {CAMPAIGN_PHONE}. "
        f"Join https://t.me/RichPlanOfficial",
    ),
    (
        "Ponzi recruitment SMS (variant)",
        12,
        f"RichPlan Investment: Guaranteed 12% daily returns! Referral bonus on every downline "
        f"member. Joining package Rs 9000. Pay {CAMPAIGN_UPI} or call {CAMPAIGN_PHONE}. "
        f"Join https://t.me/RichPlanOfficial",
    ),
    (
        "Loan app distribution SMS",
        10,
        f"Instant loan in 5 minutes! No CIBIL check, only Aadhaar needed. "
        f"Download now http://{CAMPAIGN_HOST}/quickcash.apk Support {CAMPAIGN_PHONE}",
    ),
    (
        "SBI KYC phishing",
        15,
        "Dear customer your SBI KYC will be blocked in 24 hours. Verify immediately at "
        "https://sbi-verify-kyc.in/urgent or your account will be suspended.",
    ),
    (
        "Electricity disconnection lure",
        9,
        "Dear consumer your electricity will be disconnected tonight at 9:30 PM due to pending "
        "bill. Update meter immediately, call 9988776655.",
    ),
    (
        "OTP theft attempt",
        7,
        "This is SBI security. To stop an unauthorised transaction of Rs 48,000 please share the "
        "OTP sent to your registered mobile immediately.",
    ),
    (
        "Betting platform promotion",
        11,
        "Get your betting ID now! Colour prediction and aviator game. 100% sure shot tips, "
        "welcome bonus 500, instant withdrawal. WhatsApp 9876501234",
    ),
    (
        "Courier customs scam",
        5,
        "Your parcel is held at customs. Pay clearance duty of Rs 2,450 within 12 hours to "
        "release it, or it will be returned. Track: https://parcel-release-in.xyz/pay",
    ),
    (
        "Fake job offer",
        4,
        "Work from home! Earn Rs 800-1500 per hour by liking YouTube videos. Registration fee "
        "Rs 500 only. Contact on Telegram https://t.me/EasyTaskJobs",
    ),
    (
        # The operator rotated the phone number but kept the payment account,
        # which is exactly what campaign linking is built to catch.
        "Ponzi recruitment SMS (new number)",
        3,
        f"RichPlan Investment: Guaranteed 15% daily returns! Referral bonus on every downline "
        f"member. Joining package Rs 15000. Pay {CAMPAIGN_UPI} or call {ROTATED_PHONE}. "
        f"Join https://t.me/RichPlanOfficial",
    ),
    (
        # Shares no identifier with the first KYC message; only the template
        # links them.
        "SBI KYC phishing (new domain)",
        2,
        "Dear customer your SBI KYC will be blocked in 24 hours. Verify immediately at "
        "https://sbi-kyc-update.top/verify or your account will be suspended.",
    ),
    (
        "Genuine delivery notification",
        1,
        "Your order 4471239 has been dispatched and will arrive on Tuesday between 10am and 2pm. "
        "No action is needed.",
    ),
)

PONZI_SITE_HTML = f"""
<html><head><title>RichPlan Investment — Guaranteed Daily Returns</title></head><body>
  <h1>Guaranteed returns on every deposit</h1>
  <p>Earn 10% daily on your investment. 100% safe, zero risk, assured profit.</p>
  <p>Referral bonus on every downline member. Binary plan and level income available.</p>
  <p>Joining package starts at Rs 5000. Activate your ID today and start earning!</p>
  <p>Silver, Gold and Platinum member plans. Limited slots left, hurry!</p>
  <p>Deposit via UPI {CAMPAIGN_UPI} or A/c 918273645501 IFSC HDFC0004567</p>
  <p>Support {CAMPAIGN_PHONE}. <a href="https://t.me/RichPlanOfficial">Join our Telegram channel</a></p>
  <p>SEBI approved investment scheme.</p>
</body></html>
"""

BETTING_SITE_HTML = """
<html><head><title>LuckyBet Pro</title></head><body>
  <h1>Get your betting ID instantly</h1>
  <p>Colour prediction, aviator game and crash game available 24x7.</p>
  <p>100% winning tips from our experts. Fixed matches available.</p>
  <p>Welcome bonus on first deposit. Instant withdrawal guaranteed.</p>
  <p>Deposit via UPI luckybet@okaxis or contact 9876501234</p>
</body></html>
"""

APK_SPECS: tuple[dict, ...] = (
    {
        "label": "QuickCash Loan",
        "days_ago": 6,
        "package": "com.quickcash.instantloan",
        "target_sdk": 22,
        "permissions": (
            "android.permission.READ_SMS",
            "android.permission.RECEIVE_SMS",
            "android.permission.READ_CONTACTS",
            "android.permission.READ_CALL_LOG",
            "android.permission.INTERNET",
            "android.permission.SYSTEM_ALERT_WINDOW",
            "android.permission.REQUEST_INSTALL_PACKAGES",
            "android.permission.ACCESS_FINE_LOCATION",
        ),
        "dex_strings": (
            f"http://{CAMPAIGN_HOST}/collect",
            f"upi collect request to {CAMPAIGN_UPI}",
            "https://t.me/RichPlanOfficial",
            f"support number {CAMPAIGN_PHONE}",
        ),
    },
    {
        "label": "Simple Notes",
        "days_ago": 8,
        "package": "com.example.simplenotes",
        "target_sdk": 34,
        "permissions": ("android.permission.INTERNET",),
        "dex_strings": ("https://api.simplenotes.example/v1/sync",),
    },
)


def _build_demo_apk(build_apk, build_png, index: int, spec: dict) -> bytes:
    return build_apk(
        package=spec["package"],
        label=spec["label"],
        target_sdk=spec["target_sdk"],
        permissions=spec["permissions"],
        dex_strings=spec["dex_strings"],
        icon_png=build_png(seed=index + 11),
    )


def _backdate(case: CaseRecord, days_ago: int) -> None:
    """Spread demo cases over recent weeks so campaign timelines show evolution."""

    when = datetime.now(timezone.utc) - timedelta(days=days_ago, hours=(case.id * 5) % 11)
    case.created_at = when
    case.updated_at = when
    for row in case.identifiers:
        row.created_at = when


def export_demo_apks(directory: Path) -> list[Path]:
    """Write the demo APKs to disk so they can be uploaded during a demo."""

    from tests.apk_fixtures import build_apk, build_png

    directory.mkdir(parents=True, exist_ok=True)
    written = []
    for index, spec in enumerate(APK_SPECS):
        path = directory / f"{spec['package']}.apk"
        path.write_bytes(_build_demo_apk(build_apk, build_png, index, spec))
        written.append(path)
    return written


async def _clear_cases(session) -> int:
    """Remove every case and its children.

    A bulk ``delete()`` bypasses the ORM's ``delete-orphan`` cascade, so the
    child tables are cleared explicitly. Relying on the database cascade alone
    is not enough either: SQLite enforces foreign keys only when the
    ``foreign_keys`` pragma is set, and an orphaned identifier row would keep
    appearing in the heat-list forever.
    """

    await session.execute(delete(IdentifierRecord))
    await session.execute(delete(FindingRecord))
    removed = await session.execute(delete(CaseRecord))
    return removed.rowcount or 0


async def seed_demo(reset: bool = False) -> dict[str, int]:
    settings = get_settings()
    database = build_database(settings)
    await database.create_all()

    scam = ScamAnalyzer(settings)
    enrichment = UrlEnrichmentService(settings)
    artifacts = ArtifactAnalyzer(settings, scam, EmailAnalyzer(settings, scam), enrichment)
    website = WebsiteAnalyzer(settings)
    apk_analyzer = ApkAnalyzer()

    counts = {"cleared": 0, "messages": 0, "websites": 0, "apks": 0, "blacklist": 0}

    async with database.session() as session:
        if reset:
            counts["cleared"] = await _clear_cases(session)
        counts["blacklist"] = await seed_blacklist(session)

        for label, days_ago, text in MESSAGES:
            bundle = await artifacts.analyze(
                ArtifactType.MESSAGE, text, language=InputLanguage.AUTO, session=session
            )
            case = await create_case(
                session, bundle, source=CaseSource.OFFICER, reporter_note=f"Demo data: {label}"
            )
            _backdate(case, days_ago)
            counts["messages"] += 1

        for label, days_ago, markup, url in (
            ("RichPlan Ponzi site", 8, PONZI_SITE_HTML, "https://richplan-invest.xyz/join"),
            ("LuckyBet betting site", 6, BETTING_SITE_HTML, "https://luckybet-pro.top/register"),
        ):
            page = website._build_page(url, url, 200, "text/html", markup.encode("utf-8"), [url], False)
            bundle = website.analyze_page(page)
            case = await create_case(
                session, bundle, source=CaseSource.OFFICER, reporter_note=f"Demo data: {label}"
            )
            _backdate(case, days_ago)
            counts["websites"] += 1

        try:
            from tests.apk_fixtures import build_apk, build_png
        except ImportError:
            logger.warning("apk_fixtures_unavailable: skipping demo APK cases")
        else:
            for index, spec in enumerate(APK_SPECS):
                data = _build_demo_apk(build_apk, build_png, index, spec)
                bundle = apk_analyzer.analyze(data, filename=f"{spec['package']}.apk")
                case = await create_case(
                    session,
                    bundle,
                    source=CaseSource.OFFICER,
                    reporter_note=f"Demo data: {spec['label']}",
                )
                _backdate(case, spec["days_ago"])
                counts["apks"] += 1

    await scam.close()
    await database.close()
    return counts


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo cases for the investigation dashboard.")
    parser.add_argument("--reset", action="store_true", help="Delete existing cases first")
    parser.add_argument(
        "--export-apks",
        metavar="DIR",
        type=Path,
        help="Only write the demo APK files to DIR (for upload during a demo) and exit",
    )
    args = parser.parse_args()

    if args.export_apks:
        for path in export_demo_apks(args.export_apks):
            print(path)
        return

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    counts = await seed_demo(reset=args.reset)
    logger.info(
        "demo_seeded cleared=%d messages=%d websites=%d apks=%d blacklist=%d",
        counts["cleared"],
        counts["messages"],
        counts["websites"],
        counts["apks"],
        counts["blacklist"],
    )
    print(
        f"\nSeeded {counts['messages']} messages, {counts['websites']} websites, "
        f"{counts['apks']} APKs.\n"
        f"Campaign identifiers reused across types: {CAMPAIGN_UPI}, "
        f"+91{CAMPAIGN_PHONE}, {CAMPAIGN_HOST} (phone later rotated to +91{ROTATED_PHONE})"
    )


if __name__ == "__main__":
    asyncio.run(main())
