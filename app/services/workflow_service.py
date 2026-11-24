from __future__ import annotations

"""The approval chain a requisition must pass through (planversionalpha.md D.5).

    DRAFT -submit-> PENDING_STATION -approve-> [PENDING_SUPERVISOR] -approve-> APPROVED
      ^                   |                            |                          |
      +------- return ----+--------- return -----------+                    dispatch
                                                                                  |
                                              DISPATCHED -response-> RESPONDED -close-> CLOSED

Rules enforced here rather than in the UI, because hiding a button is not
access control:

* only the role for the current stage may approve, and only within the
  document's own unit subtree;
* **the drafter may not approve their own document** - separation of duties is
  the whole point of a chain of command;
* a RETURN must carry a comment, otherwise the drafter cannot act on it;
* each approval records the body hash it applied to, so a document edited
  after approval is detectably not the one that was signed off;
* every transition writes an approvals row and an audit entry.

Escalation needs no scheduler: ``due_at`` is set when a stage starts and
"overdue" is computed on read.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Permission, Role, as_role, has_permission
from app.data.approval_policy import (
    STAGE_NONE,
    STAGE_STATION,
    STAGE_SUPERVISOR,
    first_stage,
    next_stage,
    policy_for,
)
from app.db.models import ApprovalRecord, DocumentRecord, DocumentVersionRecord, UserRecord
from app.services import audit_service, document_service

logger = logging.getLogger(__name__)

DRAFT = "DRAFT"
RETURNED = "RETURNED"
PENDING_STATION = "PENDING_STATION"
PENDING_SUPERVISOR = "PENDING_SUPERVISOR"
APPROVED = "APPROVED"
DISPATCHED = "DISPATCHED"
RESPONDED = "RESPONDED"
CLOSED = "CLOSED"
CANCELLED = "CANCELLED"

EDITABLE = {DRAFT, RETURNED}
PENDING = {PENDING_STATION: STAGE_STATION, PENDING_SUPERVISOR: STAGE_SUPERVISOR}

# Which roles may clear which stage.
STAGE_ROLES: dict[str, frozenset[Role]] = {
    STAGE_STATION: frozenset({Role.STATION_HEAD, Role.SUPERVISOR, Role.ADMIN, Role.OFFICER}),
    STAGE_SUPERVISOR: frozenset({Role.SUPERVISOR, Role.ADMIN, Role.OFFICER}),
}


class WorkflowError(ValueError):
    """A transition that the state machine does not allow."""

    def __init__(self, message: str, *, status_code: int = 422) -> None:
        super().__init__(message)
        self.status_code = status_code


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def is_overdue(document: DocumentRecord, now: datetime | None = None) -> bool:
    due = _utc(document.due_at)
    if due is None or document.status not in PENDING:
        return False
    return (now or datetime.now(timezone.utc)) > due


def _start_stage(document: DocumentRecord, stage: str) -> None:
    policy = policy_for(document.doc_type)
    document.current_stage = stage
    document.status = PENDING_STATION if stage == STAGE_STATION else PENDING_SUPERVISOR
    document.due_at = datetime.now(timezone.utc) + timedelta(hours=policy.sla_hours)


def _can_act_on_stage(user: UserRecord, stage: str) -> bool:
    return as_role(user.role) in STAGE_ROLES.get(stage, frozenset())


def _same_subtree(user: UserRecord, document: DocumentRecord) -> bool:
    """The approver must be in, or above, the document's own unit."""

    if as_role(user.role) in {Role.ADMIN, Role.OFFICER}:
        return True
    unit = getattr(user, "unit", None)
    path = getattr(unit, "path", None)
    if not path:
        return False
    doc_path = document.unit_path or "/"
    # Either the document is inside the approver's subtree, or the approver's
    # unit is an ancestor of it (a supervisor approving a station's document).
    return doc_path.startswith(path) or path.startswith(doc_path)


async def _record(
    session: AsyncSession,
    document: DocumentRecord,
    user: UserRecord,
    *,
    stage: str,
    action: str,
    comment: str | None,
) -> None:
    session.add(
        ApprovalRecord(
            document_id=document.id,
            stage=stage,
            actor_id=user.id,
            actor_name=user.username,
            actor_rank=getattr(user, "rank", None),
            action=action,
            comment=comment,
            body_sha256=document.body_sha256,
        )
    )
    await audit_service.append_event(
        session,
        action=f"document.{action.lower()}",
        actor=user,
        target_type="document",
        target_id=document.doc_no,
        details={
            "doc_type": document.doc_type,
            "stage": stage,
            "status": document.status,
            "body_sha256": document.body_sha256,
            "comment": comment,
        },
    )


async def submit(session: AsyncSession, document: DocumentRecord, user: UserRecord) -> DocumentRecord:
    if document.status not in EDITABLE:
        raise WorkflowError(f"Only a draft or returned document can be submitted (this one is {document.status}).")
    if not has_permission(user.role, Permission.DOCUMENT_DRAFT):
        raise WorkflowError("Your role may not submit documents for approval.", status_code=403)
    _start_stage(document, first_stage(document.doc_type, _amount_of(document)))
    await _record(session, document, user, stage=document.current_stage, action="SUBMIT", comment=None)
    await session.flush()
    return document


async def approve(
    session: AsyncSession, document: DocumentRecord, user: UserRecord, *, comment: str | None = None
) -> DocumentRecord:
    stage = PENDING.get(document.status)
    if stage is None:
        raise WorkflowError(f"This document is not awaiting approval (it is {document.status}).")
    if not _can_act_on_stage(user, stage):
        raise WorkflowError(
            f"{stage.title()} approval needs a "
            + ("station head or supervisor." if stage == STAGE_STATION else "supervisor."),
            status_code=403,
        )
    if not _same_subtree(user, document):
        raise WorkflowError("This document belongs to another unit.", status_code=403)
    if document.created_by is not None and document.created_by == user.id:
        # Separation of duties: the drafter is not the approver.
        raise WorkflowError(
            "You drafted this document, so you cannot also approve it. It needs another officer.",
            status_code=403,
        )

    await _record(session, document, user, stage=stage, action="APPROVE", comment=comment)
    following = next_stage(document.doc_type, stage, _amount_of(document))
    if following == STAGE_NONE:
        document.status = APPROVED
        document.current_stage = STAGE_NONE
        document.due_at = None
    else:
        _start_stage(document, following)
    await session.flush()
    return document


async def send_back(
    session: AsyncSession, document: DocumentRecord, user: UserRecord, *, comment: str
) -> DocumentRecord:
    stage = PENDING.get(document.status)
    if stage is None:
        raise WorkflowError(f"This document is not awaiting approval (it is {document.status}).")
    if not _can_act_on_stage(user, stage):
        raise WorkflowError("Your role may not act on this stage.", status_code=403)
    if not (comment or "").strip():
        raise WorkflowError("Say what needs to change: a returned document needs a reason.")

    document.status = RETURNED
    document.current_stage = STAGE_NONE
    document.due_at = None
    await _record(session, document, user, stage=stage, action="RETURN", comment=comment.strip())
    await session.flush()
    return document


async def edit(
    session: AsyncSession, document: DocumentRecord, user: UserRecord, *, body_html: str
) -> DocumentRecord:
    if document.status not in EDITABLE:
        raise WorkflowError(
            f"A document can only be edited while it is a draft or has been returned (this one is {document.status})."
        )
    document.version += 1
    document.body_html = body_html
    document.body_sha256 = document_service.body_hash(body_html)
    document.status = DRAFT
    session.add(
        DocumentVersionRecord(
            document_id=document.id,
            version=document.version,
            body_html=body_html,
            body_sha256=document.body_sha256,
            edited_by=user.id,
        )
    )
    await audit_service.append_event(
        session,
        action="document.edit",
        actor=user,
        target_type="document",
        target_id=document.doc_no,
        details={"version": document.version, "body_sha256": document.body_sha256},
    )
    await session.flush()
    return document


async def dispatch(
    session: AsyncSession,
    document: DocumentRecord,
    user: UserRecord,
    *,
    channel: str,
    reference: str,
) -> DocumentRecord:
    if document.status != APPROVED:
        raise WorkflowError("Only an approved document can be dispatched.")
    if not (reference or "").strip():
        raise WorkflowError("Record the dispatch reference (email id, portal ticket or despatch number).")
    document.status = DISPATCHED
    document.dispatched_at = datetime.now(timezone.utc)
    document.dispatch_channel = channel
    document.dispatch_ref = reference.strip()[:120]
    await _record(session, document, user, stage=STAGE_NONE, action="DISPATCH", comment=f"{channel}: {reference}")
    await session.flush()
    return document


async def record_response(
    session: AsyncSession, document: DocumentRecord, user: UserRecord, *, note: str
) -> DocumentRecord:
    if document.status not in {DISPATCHED, RESPONDED}:
        raise WorkflowError("A response can only be recorded against a dispatched document.")
    document.status = RESPONDED
    document.response_received_at = datetime.now(timezone.utc)
    document.response_note = (note or "").strip()[:4000]
    await _record(session, document, user, stage=STAGE_NONE, action="RESPONSE", comment=document.response_note)
    await session.flush()
    return document


async def close(session: AsyncSession, document: DocumentRecord, user: UserRecord) -> DocumentRecord:
    if document.status not in {RESPONDED, DISPATCHED}:
        raise WorkflowError("Only a dispatched or answered document can be closed.")
    document.status = CLOSED
    await _record(session, document, user, stage=STAGE_NONE, action="CLOSE", comment=None)
    await session.flush()
    return document


async def cancel(
    session: AsyncSession, document: DocumentRecord, user: UserRecord, *, reason: str
) -> DocumentRecord:
    if document.status in {CLOSED, CANCELLED}:
        raise WorkflowError("This document is already finished.")
    if not (reason or "").strip():
        raise WorkflowError("Give a reason for cancelling the document.")
    document.status = CANCELLED
    document.current_stage = STAGE_NONE
    document.due_at = None
    await _record(session, document, user, stage=STAGE_NONE, action="CANCEL", comment=reason.strip())
    await session.flush()
    return document


def _amount_of(document: DocumentRecord) -> int | None:
    case = getattr(document, "case", None)
    return getattr(case, "amount_lost", None)


async def pending_for(session: AsyncSession, user: UserRecord, *, limit: int = 50) -> list[DocumentRecord]:
    """Documents waiting for this officer, most overdue first."""

    stages = [stage for stage, roles in STAGE_ROLES.items() if as_role(user.role) in roles]
    if not stages:
        return []
    statuses = [status for status, stage in PENDING.items() if stage in stages]
    rows = (
        (
            await session.execute(
                select(DocumentRecord)
                .where(DocumentRecord.status.in_(statuses))
                .order_by(DocumentRecord.due_at.asc())
                .limit(max(1, min(limit, 200)))
            )
        )
        .scalars()
        .all()
    )
    # A supervisor should not see another district's queue.
    return [row for row in rows if _same_subtree(user, row)]


__all__ = [
    "APPROVED",
    "CANCELLED",
    "CLOSED",
    "DISPATCHED",
    "DRAFT",
    "EDITABLE",
    "PENDING",
    "PENDING_STATION",
    "PENDING_SUPERVISOR",
    "RESPONDED",
    "RETURNED",
    "WorkflowError",
    "approve",
    "cancel",
    "close",
    "dispatch",
    "edit",
    "is_overdue",
    "pending_for",
    "record_response",
    "send_back",
    "submit",
]
