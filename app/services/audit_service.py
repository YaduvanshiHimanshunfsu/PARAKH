from __future__ import annotations

"""Tamper-evident audit log (planversionalpha.md C.5).

Each entry hashes the previous entry's hash together with its own canonical
body::

    entry_hash = SHA-256(prev_hash + canonical_json(body))

Editing or deleting any row therefore breaks every link after it, and
``verify_chain`` reports the first sequence number where the chain fails.
This does not stop a determined administrator with database access from
rewriting the whole chain; it makes a *partial* edit detectable, which is what
an evidence trail needs.

Writes are serialised: SQLite serialises them anyway, and on PostgreSQL the
append takes a transaction-scoped advisory lock so two officers acting at the
same moment cannot claim the same sequence number.
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditEvent, UserRecord

logger = logging.getLogger(__name__)

GENESIS_HASH = "0" * 64

# One constant for the advisory lock, so every append contends on the same key.
_PG_ADVISORY_LOCK_KEY = 0x50524B48  # "PRKH"


class Action:
    """Actions worth recording. Strings, so a new one needs no migration."""

    LOGIN = "login"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    CASE_VIEW = "case.view"
    CASE_CREATE = "case.create"
    CASE_UPDATE = "case.update"
    CASE_ASSIGN = "case.assign"
    CASE_TRANSFER = "case.transfer"
    CASE_VERIFY = "case.verify"
    IDENTIFIER_ROLE_CHANGE = "identifier.role_change"
    EXPORT_FULL = "export.full"
    EXPORT_REDACTED = "export.redacted"
    REPORT_VIEW = "report.view"


@dataclass(frozen=True)
class ChainStatus:
    intact: bool
    events: int
    broken_at: int | None = None

    @property
    def summary(self) -> str:
        if self.events == 0:
            return "No audit events recorded yet."
        if self.intact:
            return f"Audit chain verified ({self.events} events)."
        return f"Audit chain broken at event {self.broken_at} of {self.events}."


def _utc(value: datetime) -> datetime:
    """Normalise a timestamp for hashing.

    SQLite hands back a naive datetime even for a column declared with a
    timezone, and ``astimezone`` would then read it as *local* time and shift
    it, so a chain written on one machine would verify as broken on reading.
    A naive value is always UTC here, because that is what is written.
    """

    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def canonical_body(
    seq: int, at: datetime, actor_id: int | None, actor_name: str, actor_role: str,
    action: str, target_type: str, target_id: str, details: dict,
) -> str:
    """Byte-identical rendering of an entry, so the hash is reproducible."""

    return json.dumps(
        {
            "seq": seq,
            "at": _utc(at).isoformat(timespec="microseconds"),
            "actor": actor_id,
            "actor_name": actor_name,
            "actor_role": actor_role,
            "action": action,
            "target": [target_type, target_id],
            "details": details,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def entry_hash(prev_hash: str, body: str) -> str:
    return hashlib.sha256((prev_hash + body).encode("utf-8")).hexdigest()


async def append_event(
    session: AsyncSession,
    *,
    action: str,
    actor: UserRecord | None = None,
    target_type: str = "",
    target_id: str = "",
    details: dict | None = None,
) -> AuditEvent:
    """Append one entry and link it to the previous one."""

    if session.bind is not None and session.bind.dialect.name == "postgresql":
        await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": _PG_ADVISORY_LOCK_KEY})

    last = (
        await session.execute(select(AuditEvent).order_by(AuditEvent.seq.desc()).limit(1))
    ).scalar_one_or_none()
    seq = (last.seq + 1) if last else 1
    prev_hash = last.entry_hash if last else GENESIS_HASH
    at = datetime.now(timezone.utc)
    payload = dict(details or {})

    body = canonical_body(
        seq, at,
        actor.id if actor else None,
        actor.username if actor else "system",
        (actor.role if actor else "SYSTEM") or "SYSTEM",
        action, target_type, target_id, payload,
    )
    event = AuditEvent(
        seq=seq,
        at=at,
        actor_id=actor.id if actor else None,
        actor_name=actor.username if actor else "system",
        actor_role=(actor.role if actor else "SYSTEM") or "SYSTEM",
        action=action,
        target_type=target_type,
        target_id=str(target_id)[:64],
        details=payload,
        prev_hash=prev_hash,
        entry_hash=entry_hash(prev_hash, body),
    )
    session.add(event)
    await session.flush()
    return event


def verify_chain(events: list[AuditEvent]) -> ChainStatus:
    """Return the first broken sequence number, or report the chain intact."""

    ordered = sorted(events, key=lambda event: event.seq)
    previous = GENESIS_HASH
    expected_seq = 1
    for event in ordered:
        if event.seq != expected_seq or event.prev_hash != previous:
            return ChainStatus(False, len(ordered), event.seq)
        body = canonical_body(
            event.seq, event.at, event.actor_id, event.actor_name, event.actor_role,
            event.action, event.target_type, event.target_id, event.details or {},
        )
        if entry_hash(event.prev_hash, body) != event.entry_hash:
            return ChainStatus(False, len(ordered), event.seq)
        previous = event.entry_hash
        expected_seq += 1
    return ChainStatus(True, len(ordered))


async def verify_stored_chain(session: AsyncSession) -> ChainStatus:
    events = list((await session.execute(select(AuditEvent).order_by(AuditEvent.seq))).scalars().all())
    return verify_chain(events)


async def events_for_target(
    session: AsyncSession, target_type: str, target_id: str, *, limit: int = 100
) -> list[AuditEvent]:
    statement = (
        select(AuditEvent)
        .where(AuditEvent.target_type == target_type, AuditEvent.target_id == str(target_id))
        .order_by(AuditEvent.seq.desc())
        .limit(max(1, min(limit, 500)))
    )
    return list((await session.execute(statement)).scalars().all())


__all__ = [
    "Action",
    "ChainStatus",
    "GENESIS_HASH",
    "append_event",
    "canonical_body",
    "entry_hash",
    "events_for_target",
    "verify_chain",
    "verify_stored_chain",
]
