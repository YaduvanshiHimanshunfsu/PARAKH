from __future__ import annotations

"""Cross-source linking, similarity detection, and the heat-list.

This is the layer that answers PS01's central complaint: *"These threats often
reuse the same domains, app identifiers, phone numbers and payment accounts,
yet they are reported and examined separately."*

Three capabilities:

* **Linking** — given a case, find every other case sharing an identifier,
  ranked so a shared phone number outweighs a shared URL shortener.
* **Similarity** — exact template matches via normalised hash, near-duplicates
  via SimHash Hamming distance.
* **Heat-list** — the most frequently reported identifiers, with a recency trend.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CaseRecord, IdentifierRecord
from app.schemas import (
    CaseSummary,
    HeatListEntry,
    Identifier,
    IdentifierType,
    LinkedCase,
    ReportedIdentifier,
    RiskLevel,
    SimilarCase,
)
from app.services.case_service import to_summary
from app.utils.fingerprint import NEAR_DUPLICATE_THRESHOLD, hamming_distance

logger = logging.getLogger(__name__)

# How much a shared identifier contributes to a link score. A phone number or
# payment account is a far stronger connection than a shared shortener domain,
# which thousands of unrelated messages have.
_IDENTIFIER_WEIGHT: dict[IdentifierType, int] = {
    IdentifierType.UPI: 10,
    IdentifierType.BANK_ACCOUNT: 10,
    IdentifierType.IFSC: 6,
    IdentifierType.CRYPTO_BTC: 10,
    IdentifierType.CRYPTO_ETH: 10,
    IdentifierType.PHONE: 9,
    IdentifierType.CERT_SHA256: 10,
    IdentifierType.ICON_PHASH: 7,
    IdentifierType.PACKAGE: 8,
    IdentifierType.TELEGRAM: 8,
    IdentifierType.IP: 7,
    IdentifierType.EMAIL: 6,
    IdentifierType.DOMAIN: 5,
    IdentifierType.URL: 3,
}
_DEFAULT_WEIGHT = 4

_SIMILARITY_SCAN_LIMIT = 2_000


def identifier_weight(identifier_type: IdentifierType) -> int:
    return _IDENTIFIER_WEIGHT.get(identifier_type, _DEFAULT_WEIGHT)


_NON_LINKING_TYPES = frozenset({IdentifierType.URL, IdentifierType.IFSC})

GENERIC_HOSTS = frozenset({
    "t.me", "telegram.me", "telegram.org", "wa.me", "whatsapp.com", "chat.whatsapp.com",
    "api.whatsapp.com", "bit.ly", "tinyurl.com", "goo.gl", "rb.gy", "cutt.ly", "is.gd",
    "shorturl.at", "tiny.cc", "youtube.com", "youtu.be", "google.com", "play.google.com",
    "docs.google.com", "drive.google.com", "forms.gle", "facebook.com", "fb.me",
    "instagram.com", "x.com", "twitter.com", "linkedin.com", "github.com", "gmail.com",
    "yahoo.com", "outlook.com", "hotmail.com",
})


def _identifier_type(value: str) -> IdentifierType | None:
    try:
        return IdentifierType(value)
    except ValueError:
        return None


def links_cases(type_value: str, value: str) -> bool:
    """Whether a shared identifier of this kind means a shared operator."""

    identifier_type = _identifier_type(type_value)
    if identifier_type is None or identifier_type in _NON_LINKING_TYPES:
        return False
    if identifier_type is IdentifierType.DOMAIN and value.lower().removeprefix("www.") in GENERIC_HOSTS:
        return False
    return identifier_weight(identifier_type) >= 5


async def cases_for_identifier(
    session: AsyncSession,
    identifier_type: IdentifierType,
    value: str,
    *,
    limit: int = 100,
) -> list[CaseSummary]:
    """Every case in which this exact identifier appears, newest first."""

    statement = (
        select(CaseRecord)
        .join(IdentifierRecord, IdentifierRecord.case_id == CaseRecord.id)
        .where(
            IdentifierRecord.type == identifier_type.value,
            IdentifierRecord.value == value.strip().lower()
            if identifier_type is not IdentifierType.CRYPTO_BTC
            else IdentifierRecord.value == value.strip(),
        )
        .order_by(CaseRecord.created_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(statement)).scalars().unique().all()
    return [to_summary(row) for row in rows]


async def linked_cases(
    session: AsyncSession, case_id: str, *, limit: int = 25
) -> list[LinkedCase]:
    """Find cases sharing identifiers with this one, ranked by link strength."""

    case = (
        await session.execute(select(CaseRecord).where(CaseRecord.case_id == case_id))
    ).scalar_one_or_none()
    if case is None:
        return []

    own = [(row.type, row.value) for row in case.identifiers]
    if not own:
        return []

    values = {value for _, value in own}
    rows = (
        (
            await session.execute(
                select(IdentifierRecord)
                .where(IdentifierRecord.value.in_(values), IdentifierRecord.case_id != case.id)
            )
        )
        .scalars()
        .all()
    )
    if not rows:
        return []

    own_pairs = set(own)
    by_case: dict[int, list[IdentifierRecord]] = defaultdict(list)
    for row in rows:
        if (row.type, row.value) in own_pairs:
            by_case[row.case_id].append(row)
    if not by_case:
        return []

    others = (
        (await session.execute(select(CaseRecord).where(CaseRecord.id.in_(by_case.keys()))))
        .scalars()
        .unique()
        .all()
    )

    linked: list[LinkedCase] = []
    for other in others:
        shared = by_case[other.id]
        strength = sum(
            _IDENTIFIER_WEIGHT.get(_as_type(row.type), _DEFAULT_WEIGHT) for row in shared
        )
        linked.append(
            LinkedCase(
                case=to_summary(other),
                shared_identifiers=[
                    f"{row.type}:{row.value}" for row in sorted(shared, key=lambda r: r.type)
                ][:10],
                link_strength=min(100, strength),
            )
        )

    # Strongest links first; within equal strength, the most recent case first.
    linked.sort(key=lambda item: (item.link_strength, item.case.created_at), reverse=True)
    return linked[:limit]


async def similar_cases(
    session: AsyncSession, case_id: str, *, limit: int = 25
) -> list[SimilarCase]:
    """Exact template matches and near-duplicates of this case's content."""

    case = (
        await session.execute(select(CaseRecord).where(CaseRecord.case_id == case_id))
    ).scalar_one_or_none()
    if case is None or not case.content_sha256:
        return []

    results: list[SimilarCase] = []
    seen: set[int] = {case.id}

    exact_rows = (
        (
            await session.execute(
                select(CaseRecord).where(
                    CaseRecord.content_sha256 == case.content_sha256,
                    CaseRecord.id != case.id,
                )
            )
        )
        .scalars()
        .unique()
        .all()
    )
    for row in exact_rows:
        seen.add(row.id)
        results.append(
            SimilarCase(case=to_summary(row), match_type="EXACT_TEMPLATE", distance=0, similarity=100)
        )

    if case.simhash:
        candidates = (
            (
                await session.execute(
                    select(CaseRecord)
                    .where(
                        CaseRecord.simhash.is_not(None),
                        CaseRecord.id != case.id,
                        CaseRecord.artifact_type == case.artifact_type,
                    )
                    .order_by(CaseRecord.created_at.desc())
                    .limit(_SIMILARITY_SCAN_LIMIT)
                )
            )
            .scalars()
            .unique()
            .all()
        )
        for row in candidates:
            if row.id in seen:
                continue
            distance = hamming_distance(case.simhash, row.simhash or "")
            if distance <= NEAR_DUPLICATE_THRESHOLD:
                seen.add(row.id)
                results.append(
                    SimilarCase(
                        case=to_summary(row),
                        match_type="NEAR_DUPLICATE",
                        # Scaled so the threshold maps to roughly 50% similarity.
                        distance=distance,
                        similarity=max(0, 100 - round(distance * 100 / (NEAR_DUPLICATE_THRESHOLD * 2))),
                    )
                )

    results.sort(key=lambda item: item.distance)
    return results[:limit]


async def heat_list(
    session: AsyncSession,
    *,
    identifier_type: IdentifierType | None = None,
    days: int | None = None,
    limit: int = 25,
) -> list[HeatListEntry]:
    """Most frequently reported identifiers, with a recent-activity trend.

    PS01 asks for "a heat-list of the most frequently reported domains, phone
    numbers, apps and payment identifiers".
    """

    limit = max(1, min(limit, 200))
    recent_cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    statement = select(
        IdentifierRecord.type,
        IdentifierRecord.value,
        func.count(func.distinct(IdentifierRecord.case_id)).label("case_count"),
        func.min(IdentifierRecord.created_at).label("first_seen"),
        func.max(IdentifierRecord.created_at).label("last_seen"),
    ).group_by(IdentifierRecord.type, IdentifierRecord.value)

    if identifier_type is not None:
        statement = statement.where(IdentifierRecord.type == identifier_type.value)
    if days is not None:
        statement = statement.where(
            IdentifierRecord.created_at >= datetime.now(timezone.utc) - timedelta(days=days)
        )

    rows = (
        await session.execute(
            statement.order_by(func.count(func.distinct(IdentifierRecord.case_id)).desc()).limit(limit)
        )
    ).all()
    if not rows:
        return []

    recent_rows = (
        await session.execute(
            select(
                IdentifierRecord.type,
                IdentifierRecord.value,
                func.count(func.distinct(IdentifierRecord.case_id)),
            )
            .where(IdentifierRecord.created_at >= recent_cutoff)
            .group_by(IdentifierRecord.type, IdentifierRecord.value)
        )
    ).all()
    recent = {(row[0], row[1]): row[2] for row in recent_rows}

    entries: list[HeatListEntry] = []
    for type_value, value, count, first_seen, last_seen in rows:
        entries.append(
            HeatListEntry(
                type=_as_type(type_value),
                value=value,
                case_count=count,
                recent_case_count=recent.get((type_value, value), 0),
                first_seen=_iso(first_seen),
                last_seen=_iso(last_seen),
            )
        )
    return entries


async def precheck_url(session: AsyncSession, url: str) -> tuple[int, list[str]]:
    """How many prior cases cite this URL's host, and why that matters.

    Deliberately cheap — an indexed identifier lookup and a blacklist check, no
    fetching and no AI — so the browser extension and bot can call it inline
    before a user opens a link.
    """

    from urllib.parse import urlsplit

    from app.db.models import BlacklistEntry

    candidate = url if "://" in url else f"https://{url}"
    host = (urlsplit(candidate).hostname or "").lower().removeprefix("www.")
    if not host:
        return 0, []

    reasons: list[str] = []

    reported = (
        await session.execute(
            select(func.count(func.distinct(IdentifierRecord.case_id))).where(
                IdentifierRecord.type.in_(
                    (IdentifierType.DOMAIN.value, IdentifierType.IP.value)
                ),
                IdentifierRecord.value == host,
            )
        )
    ).scalar_one()
    if reported:
        reasons.append(
            f"This address appears in {reported} previously reported case"
            f"{'s' if reported != 1 else ''}."
        )

    listed = (
        await session.execute(
            select(BlacklistEntry).where(BlacklistEntry.value == host)
        )
    ).scalar_one_or_none()
    if listed is not None:
        reasons.append(f"It is on the reviewed blacklist ({listed.source}). {listed.reason}".strip())

    return reported, reasons


async def reported_matches(
    session: AsyncSession, identifiers: list[Identifier], *, limit: int = 20
) -> list[ReportedIdentifier]:
    """Which of these identifiers already appear in HIGH-risk cases, and how often.

    Read-only, so Citizen Mode can call it without storing anything. Only
    HIGH-risk cases count: a benign app that an officer once analysed must not
    make an unrelated upload look "previously reported".
    """

    keys = {
        (identifier.type.value, identifier.value)
        for identifier in identifiers
        if links_cases(identifier.type.value, identifier.value)
    }
    if not keys:
        return []

    rows = (
        await session.execute(
            select(
                IdentifierRecord.type,
                IdentifierRecord.value,
                func.count(func.distinct(CaseRecord.id)),
            )
            .join(CaseRecord, CaseRecord.id == IdentifierRecord.case_id)
            .where(
                IdentifierRecord.value.in_({value for _, value in keys}),
                CaseRecord.risk_level == RiskLevel.HIGH.value,
            )
            .group_by(IdentifierRecord.type, IdentifierRecord.value)
        )
    ).all()

    matches = [
        ReportedIdentifier(type=IdentifierType(type_value), value=value, case_count=count)
        for type_value, value, count in rows
        if (type_value, value) in keys
    ]
    matches.sort(key=lambda item: (-identifier_weight(item.type), -item.case_count, item.value))
    return matches[:limit]


def _as_type(value: str) -> IdentifierType:
    try:
        return IdentifierType(value)
    except ValueError:
        return IdentifierType.DOMAIN


def _iso(value: datetime | None) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()
