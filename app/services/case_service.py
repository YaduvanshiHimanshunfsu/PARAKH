from __future__ import annotations

"""The single pipeline every analyser feeds into.

Message, URL, email, APK and website analysers all emit an ``AnalysisBundle``;
this module is the only place that turns one into a persisted, searchable case.
Keeping persistence in one place is what lets Citizen Mode stay ephemeral — it
simply never calls in here (DECISIONS.md ADR-001).
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CaseRecord, FindingRecord, IdentifierRecord, UserRecord, new_case_id
from app.schemas import (
    AnalysisBundle,
    ArtifactType,
    CaseDetail,
    CaseSearchResponse,
    CaseSource,
    CaseStatus,
    CaseStatusUpdate,
    CaseSummary,
    Finding,
    Identifier,
    IdentifierType,
    RiskLevel,
    Severity,
    Verdict,
)
from app.utils.fingerprint import content_hash, simhash

logger = logging.getLogger(__name__)

_PREVIEW_LENGTH = 240


def derive_risk_level(score: int, verdict: Verdict | None = None) -> RiskLevel:
    """Single mapping from score/verdict to PS01's Low/Medium/High.

    Centralised deliberately: if this lived in each analyser the levels would
    drift apart and the dashboard would be inconsistent.
    """

    if verdict is Verdict.SCAM or score >= 70:
        return RiskLevel.HIGH
    if verdict is Verdict.SUSPICIOUS or score >= 35:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


# Similarity detection looks for a reused *template*, so it only applies where
# the stored content is natural language an author wrote. An APK's content is a
# generated metadata dump whose structure is identical for every package, so
# hashing it matched unrelated apps against each other at ~66% similarity. For
# apps, the real "same operator" signal is a shared signing certificate or icon
# hash, which the identifier-linking path already covers.
_SIMILARITY_ARTIFACTS = frozenset(
    {ArtifactType.MESSAGE, ArtifactType.EMAIL, ArtifactType.WEBSITE, ArtifactType.URL}
)


def _supports_similarity(bundle: AnalysisBundle, text: str) -> bool:
    return bool(text) and bundle.artifact_type in _SIMILARITY_ARTIFACTS


def _as_utc(value: datetime | None) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:  # SQLite hands back naive datetimes
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _preview(case: CaseRecord) -> str:
    text = (case.content_text or case.summary or "").strip().replace("\n", " ")
    return text[:_PREVIEW_LENGTH]


def to_summary(case: CaseRecord) -> CaseSummary:
    return CaseSummary(
        case_id=case.case_id,
        artifact_type=ArtifactType(case.artifact_type),
        risk_level=RiskLevel(case.risk_level),
        risk_score=case.risk_score,
        status=CaseStatus(case.status),
        source=CaseSource(case.source),
        summary=case.summary or "",
        preview=_preview(case),
        identifier_count=len(case.identifiers),
        finding_count=len(case.findings),
        created_at=_as_utc(case.created_at),
    )


def to_detail(case: CaseRecord) -> CaseDetail:
    return CaseDetail(
        **to_summary(case).model_dump(),
        content_text=case.content_text,
        reporter_note=case.reporter_note,
        officer_note=case.officer_note,
        findings=[
            Finding(
                code=row.code,
                severity=Severity(row.severity),
                explanation=row.explanation,
                evidence=row.evidence,
            )
            for row in case.findings
        ],
        identifiers=[
            Identifier(
                type=IdentifierType(row.type),
                value=row.value,
                raw_value=row.raw_value,
                context=row.context,
                confidence=row.confidence,
            )
            for row in case.identifiers
        ],
        details=case.details or {},
    )


async def create_case(
    session: AsyncSession,
    bundle: AnalysisBundle,
    *,
    source: CaseSource = CaseSource.OFFICER,
    reporter_note: str | None = None,
    user: UserRecord | None = None,
) -> CaseRecord:
    """Persist one analysed artifact with its findings and identifiers."""

    text = bundle.content_text or ""
    case = CaseRecord(
        case_id=new_case_id(),
        artifact_type=bundle.artifact_type.value,
        risk_level=bundle.risk_level.value,
        risk_score=bundle.risk_score,
        verdict=bundle.verdict.value if bundle.verdict else None,
        summary=bundle.summary,
        status=CaseStatus.NEW.value,
        source=source.value,
        content_text=bundle.content_text,
        content_sha256=bundle.content_sha256 or (content_hash(text) if text else None),
        simhash=bundle.simhash or (simhash(text) if _supports_similarity(bundle, text) else None),
        reporter_note=reporter_note,
        details=bundle.details or {},
        created_by=user.id if user else None,
    )
    session.add(case)
    await session.flush()  # assign case.id before attaching children

    for finding in bundle.findings:
        session.add(
            FindingRecord(
                case_id=case.id,
                code=finding.code,
                severity=finding.severity.value,
                explanation=finding.explanation,
                evidence=finding.evidence,
            )
        )

    # The unique constraint is per (case, type, value); de-duplicate in memory
    # so one malformed bundle cannot abort the whole transaction.
    seen: set[tuple[str, str]] = set()
    for identifier in bundle.identifiers:
        key = (identifier.type.value, identifier.value)
        if key in seen:
            continue
        seen.add(key)
        session.add(
            IdentifierRecord(
                case_id=case.id,
                type=identifier.type.value,
                value=identifier.value,
                raw_value=identifier.raw_value,
                context=identifier.context,
                confidence=identifier.confidence,
            )
        )

    await session.flush()
    await session.refresh(case, attribute_names=["findings", "identifiers"])
    logger.info(
        "case_created case_id=%s type=%s risk=%s findings=%d identifiers=%d",
        case.case_id,
        case.artifact_type,
        case.risk_level,
        len(bundle.findings),
        len(seen),
    )
    return case


async def get_case(session: AsyncSession, case_id: str) -> CaseRecord | None:
    return (
        await session.execute(select(CaseRecord).where(CaseRecord.case_id == case_id))
    ).scalar_one_or_none()


def _apply_filters(
    statement: Select,
    *,
    query: str | None,
    artifact_type: ArtifactType | None,
    risk_level: RiskLevel | None,
    status: CaseStatus | None,
) -> Select:
    if artifact_type is not None:
        statement = statement.where(CaseRecord.artifact_type == artifact_type.value)
    if risk_level is not None:
        statement = statement.where(CaseRecord.risk_level == risk_level.value)
    if status is not None:
        statement = statement.where(CaseRecord.status == status.value)
    if query:
        term = f"%{query.strip().lower()}%"
        # Free-text search spans the artifact itself, its summary, its public
        # reference, and any identifier extracted from it.
        identifier_match = (
            select(IdentifierRecord.case_id)
            .where(func.lower(IdentifierRecord.value).like(term))
            .scalar_subquery()
        )
        statement = statement.where(
            or_(
                func.lower(CaseRecord.content_text).like(term),
                func.lower(CaseRecord.summary).like(term),
                func.lower(CaseRecord.case_id).like(term),
                CaseRecord.id.in_(identifier_match),
            )
        )
    return statement


async def search_cases(
    session: AsyncSession,
    *,
    query: str | None = None,
    artifact_type: ArtifactType | None = None,
    risk_level: RiskLevel | None = None,
    status: CaseStatus | None = None,
    limit: int = 25,
    offset: int = 0,
) -> CaseSearchResponse:
    """Paginated case search for the investigation dashboard."""

    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    total = (
        await session.execute(
            _apply_filters(
                select(func.count(CaseRecord.id)),
                query=query,
                artifact_type=artifact_type,
                risk_level=risk_level,
                status=status,
            )
        )
    ).scalar_one()

    rows = (
        (
            await session.execute(
                _apply_filters(
                    select(CaseRecord),
                    query=query,
                    artifact_type=artifact_type,
                    risk_level=risk_level,
                    status=status,
                )
                .order_by(CaseRecord.created_at.desc(), CaseRecord.id.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )

    return CaseSearchResponse(
        total=total,
        limit=limit,
        offset=offset,
        cases=[to_summary(row) for row in rows],
    )


async def search_case_records(
    session: AsyncSession,
    *,
    query: str | None = None,
    artifact_type: ArtifactType | None = None,
    risk_level: RiskLevel | None = None,
    status: CaseStatus | None = None,
    limit: int = 1_000,
) -> list[CaseRecord]:
    """Same filters as ``search_cases`` but returns ORM rows, for bulk export."""

    statement = _apply_filters(
        select(CaseRecord),
        query=query,
        artifact_type=artifact_type,
        risk_level=risk_level,
        status=status,
    ).order_by(CaseRecord.created_at.desc()).limit(max(1, min(limit, 5_000)))
    return list((await session.execute(statement)).scalars().unique().all())


async def update_case(
    session: AsyncSession, case_id: str, update: CaseStatusUpdate
) -> CaseRecord | None:
    case = await get_case(session, case_id)
    if case is None:
        return None
    if update.status is not None:
        case.status = update.status.value
    if update.officer_note is not None:
        case.officer_note = update.officer_note
    await session.flush()
    return case
