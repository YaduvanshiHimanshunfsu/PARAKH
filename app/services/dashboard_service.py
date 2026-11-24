from __future__ import annotations

"""Officer dashboard numbers (planversionalpha.md H.6).

Every KPI, series and mix on the dashboard comes from here, computed from the
case store at request time, so nothing on the screen is a hard-coded number.
Computed in Python over the period's rows; bounded by `_MAX_ROWS`, which is
ample for a district demo (Phase F moves this to indexed SQL aggregates).
"""

from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CaseRecord
from app.schemas import DashboardSeriesPoint, DashboardSummary
from app.services import campaign_service
from app.services.case_service import to_summary

_MAX_ROWS = 20_000


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


async def build_summary(session: AsyncSession, *, days: int = 30, now: datetime | None = None) -> DashboardSummary:
    now = now or datetime.now(timezone.utc)
    start = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total = (await session.execute(select(func.count(CaseRecord.id)))).scalar_one()
    citizen_new = (
        await session.execute(
            select(func.count(CaseRecord.id)).where(CaseRecord.source == "CITIZEN", CaseRecord.status == "NEW")
        )
    ).scalar_one()
    unreviewed = (
        await session.execute(select(func.count(CaseRecord.id)).where(CaseRecord.status == "NEW"))
    ).scalar_one()

    rows = (
        (
            await session.execute(
                select(CaseRecord)
                .where(CaseRecord.created_at >= start)
                .order_by(CaseRecord.created_at.desc())
                .limit(_MAX_ROWS)
            )
        )
        .scalars()
        .unique()
        .all()
    )

    buckets: dict[str, Counter] = {
        (start + timedelta(days=offset)).date().isoformat(): Counter() for offset in range(days)
    }
    artifact_mix: Counter = Counter()
    risk_mix: Counter = Counter()
    new_today = 0
    for case in rows:
        created = _utc(case.created_at)
        key = created.date().isoformat()
        if key in buckets:
            buckets[key][case.risk_level] += 1
        artifact_mix[case.artifact_type] += 1
        risk_mix[case.risk_level] += 1
        new_today += created >= today

    graph = await campaign_service.build_campaign_graph(session, max_cases=1_000, min_cases=2)
    recent = (
        (await session.execute(select(CaseRecord).order_by(CaseRecord.created_at.desc()).limit(6)))
        .scalars()
        .unique()
        .all()
    )

    return DashboardSummary(
        days=days,
        generated_at=now.isoformat(),
        total_cases=total,
        cases_in_period=len(rows),
        high_risk_in_period=risk_mix.get("HIGH", 0),
        new_today=new_today,
        citizen_reports_new=citizen_new,
        unreviewed=unreviewed,
        campaigns=len(graph.campaigns),
        artifact_mix=dict(artifact_mix),
        risk_mix={level: risk_mix.get(level, 0) for level in ("HIGH", "MEDIUM", "LOW")},
        series=[
            DashboardSeriesPoint(date=key, high=count.get("HIGH", 0), medium=count.get("MEDIUM", 0), low=count.get("LOW", 0))
            for key, count in buckets.items()
        ],
        recent_cases=[to_summary(case) for case in recent],
    )
