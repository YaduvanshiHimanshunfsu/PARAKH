from __future__ import annotations

"""The weekly numbers a supervisor sends upward (planversionalpha.md D.7).

Every figure is computed from the case and document stores for the officer's
own jurisdiction. Nothing is estimated: if a number cannot be computed it is
reported as zero and the limitation is stated, because a report sent to a
senior officer is worse than useless if its figures are invented.
"""

import logging
import statistics
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ApprovalRecord,
    CaseRecord,
    DocumentRecord,
    IdentifierRecord,
    UnitRecord,
    UserRecord,
)
from app.schemas import MisReport, MisStationRow
from app.services.identifier_roles import LINKING_ROLES
from app.services.scoping import scope_filter
from app.services.workflow_service import is_overdue

logger = logging.getLogger(__name__)

PERIOD_DAYS = {"daily": 1, "weekly": 7, "monthly": 30}
_ROLE_VALUES = tuple(sorted(role.value for role in LINKING_ROLES))


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


async def build_report(session: AsyncSession, *, user: UserRecord, period: str = "weekly") -> MisReport:
    days = PERIOD_DAYS.get(period, 7)
    since = datetime.now(timezone.utc) - timedelta(days=days)

    cases = list(
        (
            await session.execute(
                scope_filter(select(CaseRecord).where(CaseRecord.created_at >= since), user)
            )
        )
        .scalars()
        .all()
    )
    case_ids = [case.id for case in cases]

    documents: list[DocumentRecord] = []
    if case_ids:
        documents = list(
            (
                await session.execute(
                    select(DocumentRecord).where(DocumentRecord.case_id.in_(case_ids))
                )
            )
            .scalars()
            .all()
        )

    units = {
        unit.path: unit
        for unit in (await session.execute(select(UnitRecord))).scalars().all()
    }

    by_unit: dict[str, MisStationRow] = {}
    for case in cases:
        path = case.unit_path or "/"
        unit = units.get(path)
        row = by_unit.setdefault(
            path,
            MisStationRow(
                unit_code=getattr(unit, "code", None) or "UNASSIGNED",
                unit_name=getattr(unit, "name", None) or "Unassigned intake queue",
                cases=0,
                high_risk=0,
                documents=0,
                dispatched=0,
                overdue=0,
            ),
        )
        row.cases += 1
        row.high_risk += case.risk_level == "HIGH"

    case_path = {case.id: (case.unit_path or "/") for case in cases}
    for document in documents:
        row = by_unit.get(case_path.get(document.case_id, "/"))
        if row is None:
            continue
        row.documents += 1
        row.dispatched += document.status in {"DISPATCHED", "RESPONDED", "CLOSED"}
        row.overdue += is_overdue(document)

    top_identifiers: list[dict] = []
    if case_ids:
        rows = (
            await session.execute(
                select(
                    IdentifierRecord.type,
                    IdentifierRecord.value,
                    func.count(func.distinct(IdentifierRecord.case_id)).label("cases"),
                )
                .where(
                    IdentifierRecord.case_id.in_(case_ids),
                    IdentifierRecord.role.in_(_ROLE_VALUES),
                )
                .group_by(IdentifierRecord.type, IdentifierRecord.value)
                .order_by(func.count(func.distinct(IdentifierRecord.case_id)).desc())
                .limit(10)
            )
        ).all()
        top_identifiers = [
            {"type": kind, "value": value, "cases": count} for kind, value, count in rows if count > 1
        ]

    hours = await _hours_to_approval(session, [document.id for document in documents])

    limitations = [
        "Counts cover cases created in this period within your jurisdiction.",
        "Amounts are those recorded on the case; a case with no recorded loss counts as zero.",
    ]
    if not documents:
        limitations.append("No requisitions have been drafted in this period, so document figures are zero.")
    if hours is None:
        limitations.append("No document has completed approval yet, so no approval time can be reported.")

    return MisReport(
        period=period,
        generated_at=datetime.now(timezone.utc).isoformat(),
        scope=_scope_label(user, units),
        cases=len(cases),
        high_risk_cases=sum(1 for case in cases if case.risk_level == "HIGH"),
        citizen_reports=sum(1 for case in cases if case.source == "CITIZEN"),
        amount_reported_paise=sum(case.amount_lost or 0 for case in cases),
        documents_drafted=len(documents),
        documents_dispatched=sum(
            1 for document in documents if document.status in {"DISPATCHED", "RESPONDED", "CLOSED"}
        ),
        documents_answered=sum(
            1 for document in documents if document.status in {"RESPONDED", "CLOSED"}
        ),
        documents_overdue=sum(1 for document in documents if is_overdue(document)),
        median_hours_to_approval=hours,
        by_unit=sorted(by_unit.values(), key=lambda row: (-row.cases, row.unit_code)),
        top_identifiers=top_identifiers,
        limitations=limitations,
    )


async def _hours_to_approval(session: AsyncSession, document_ids: list[int]) -> float | None:
    """Median hours from first submission to final approval."""

    if not document_ids:
        return None
    approvals = list(
        (
            await session.execute(
                select(ApprovalRecord)
                .where(ApprovalRecord.document_id.in_(document_ids))
                .order_by(ApprovalRecord.at)
            )
        )
        .scalars()
        .all()
    )
    submitted: dict[int, datetime] = {}
    durations: list[float] = []
    for approval in approvals:
        at = _utc(approval.at)
        if at is None:
            continue
        if approval.action == "SUBMIT":
            submitted.setdefault(approval.document_id, at)
        elif approval.action == "APPROVE":
            start = submitted.get(approval.document_id)
            if start is not None:
                durations.append((at - start).total_seconds() / 3600)
                submitted.pop(approval.document_id, None)
    if not durations:
        return None
    return round(statistics.median(durations), 2)


def _scope_label(user: UserRecord, units: dict[str, UnitRecord]) -> str:
    unit = getattr(user, "unit", None)
    if unit is None:
        return "All units"
    return f"{unit.name} ({unit.code}) and units below it"


__all__ = ["PERIOD_DAYS", "build_report"]
