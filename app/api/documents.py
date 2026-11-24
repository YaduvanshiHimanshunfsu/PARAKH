from __future__ import annotations

"""Action-layer endpoints: requisitions, approval chain, dispatch, MIS (D.6).

Authorisation is layered deliberately:

* ``require_officer`` decides who may reach the API at all;
* ``require_permission`` decides who may perform each action;
* jurisdiction scoping decides which documents exist for this officer, and an
  out-of-scope document answers 404 exactly like an unknown one;
* the workflow service decides whether the transition itself is legal.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import require_officer
from app.core.permissions import Permission, has_permission
from app.data.approval_policy import policy_for
from app.db.models import CaseRecord, DocumentRecord, UnitRecord, UserRecord
from app.db.session import get_session
from app.schemas import (
    ActionPackResponse,
    ApprovalEntry,
    DocumentCommentRequest,
    DocumentDetail,
    DocumentDispatchRequest,
    DocumentEditRequest,
    DocumentResponseRequest,
    DocumentReturnRequest,
    DocumentStatus,
    DocumentSummary,
    DocumentVersionEntry,
    MisReport,
    QueueResponse,
)
from app.services import audit_service, case_service, document_service, mis_service, workflow_service
from app.services.scoping import can_see_case

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/investigate", tags=["action-layer"])


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return (value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value).isoformat()


def to_summary(document: DocumentRecord, case_id: str) -> DocumentSummary:
    policy = policy_for(document.doc_type)
    return DocumentSummary(
        id=document.id,
        doc_no=document.doc_no,
        case_id=case_id,
        doc_type=document.doc_type,
        title=policy.title,
        legal_basis=policy.legal_basis,
        addressee_display=document.addressee_display,
        addressee_is_sample=document.addressee_is_sample,
        status=DocumentStatus(document.status),
        current_stage=document.current_stage,
        version=document.version,
        subject_identifiers=document.subject_identifiers or [],
        created_at=_iso(document.created_at) or "",
        due_at=_iso(document.due_at),
        overdue=workflow_service.is_overdue(document),
        dispatched_at=_iso(document.dispatched_at),
        dispatch_ref=document.dispatch_ref,
        dispatch_channel=document.dispatch_channel,
        response_received_at=_iso(document.response_received_at),
    )


def to_detail(document: DocumentRecord, case_id: str) -> DocumentDetail:
    policy = policy_for(document.doc_type)
    approvals = sorted(document.approvals, key=lambda item: item.at)
    last_approval = next(
        (item for item in reversed(approvals) if item.action == "APPROVE"), None
    )
    return DocumentDetail(
        **to_summary(document, case_id).model_dump(),
        body_html=document.body_html,
        body_sha256=document.body_sha256,
        purpose=policy.purpose,
        sla_hours=policy.sla_hours,
        response_note=document.response_note,
        approvals=[
            ApprovalEntry(
                stage=item.stage,
                actor_name=item.actor_name,
                actor_rank=item.actor_rank,
                action=item.action,
                comment=item.comment,
                body_sha256=item.body_sha256,
                at=_iso(item.at) or "",
            )
            for item in approvals
        ],
        versions=[
            DocumentVersionEntry(version=item.version, body_sha256=item.body_sha256, at=_iso(item.at) or "")
            for item in sorted(document.versions, key=lambda item: item.version)
        ],
        # The body hash recorded with the approval is compared with the body
        # now, so an edit after sign-off is visible rather than silent.
        edited_after_approval=bool(last_approval and last_approval.body_sha256 != document.body_sha256),
    )


async def _case_or_404(session: AsyncSession, case_id: str, user: UserRecord) -> CaseRecord:
    case = await case_service.get_case(session, case_id, viewer=user)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case {case_id} was not found.")
    return case


async def _document_or_404(session: AsyncSession, document_id: int, user: UserRecord) -> DocumentRecord:
    document = (
        await session.execute(
            select(DocumentRecord)
            .options(
                selectinload(DocumentRecord.approvals),
                selectinload(DocumentRecord.versions),
                selectinload(DocumentRecord.case),
            )
            .where(DocumentRecord.id == document_id)
        )
    ).scalar_one_or_none()
    if document is None or document.case is None or not can_see_case(user, document.case):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document was not found.")
    return document


def _handle(error: workflow_service.WorkflowError) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail=str(error))


# --- generation -------------------------------------------------------------


@router.post(
    "/cases/{case_id}/action-pack",
    response_model=ActionPackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Draft every requisition this case justifies",
)
async def generate_action_pack(
    case_id: str,
    session: AsyncSession = Depends(get_session),
    user: UserRecord = Depends(require_officer),
) -> ActionPackResponse:
    if not has_permission(user.role, Permission.DOCUMENT_DRAFT):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your role ({user.role}) may not draft documents.",
        )
    case = await _case_or_404(session, case_id, user)
    unit = (
        await session.execute(select(UnitRecord).where(UnitRecord.id == user.unit_id))
    ).scalar_one_or_none() if user.unit_id else None

    before = await _documents_for_case(session, case.id)
    created = await document_service.generate_action_pack(session, case, user=user, unit=unit)
    await audit_service.append_event(
        session,
        action="document.generate",
        actor=user,
        target_type="case",
        target_id=case.case_id,
        details={"created": len(created)},
    )
    all_documents = await _documents_for_case(session, case.id)
    return ActionPackResponse(
        case_id=case.case_id,
        created=len(created),
        existing=len(before),
        documents=[to_summary(item, case.case_id) for item in all_documents],
        notice=(
            "Every document is an unsigned draft. Check the addressee and the facts, then submit "
            "it for approval; nothing is sent by PARAKH."
        ),
    )


async def _documents_for_case(session: AsyncSession, case_pk: int) -> list[DocumentRecord]:
    return list(
        (
            await session.execute(
                select(DocumentRecord)
                .where(DocumentRecord.case_id == case_pk)
                .order_by(DocumentRecord.id)
            )
        )
        .scalars()
        .all()
    )


@router.get(
    "/cases/{case_id}/documents",
    response_model=list[DocumentSummary],
    summary="Requisitions drafted for this case",
)
async def list_case_documents(
    case_id: str,
    session: AsyncSession = Depends(get_session),
    user: UserRecord = Depends(require_officer),
) -> list[DocumentSummary]:
    case = await _case_or_404(session, case_id, user)
    return [to_summary(item, case.case_id) for item in await _documents_for_case(session, case.id)]


# --- one document -----------------------------------------------------------


@router.get("/documents/{document_id}", response_model=DocumentDetail, summary="One requisition")
async def get_document(
    document_id: int,
    session: AsyncSession = Depends(get_session),
    user: UserRecord = Depends(require_officer),
) -> DocumentDetail:
    document = await _document_or_404(session, document_id, user)
    return to_detail(document, document.case.case_id)


@router.get(
    "/documents/{document_id}/print",
    response_class=HTMLResponse,
    summary="Print-ready copy (A4)",
)
async def print_document(
    document_id: int,
    session: AsyncSession = Depends(get_session),
    user: UserRecord = Depends(require_officer),
) -> Response:
    document = await _document_or_404(session, document_id, user)
    await audit_service.append_event(
        session,
        action=audit_service.Action.REPORT_VIEW,
        actor=user,
        target_type="document",
        target_id=document.doc_no,
        details={"status": document.status},
    )
    return HTMLResponse(content=document.body_html)


@router.put("/documents/{document_id}", response_model=DocumentDetail, summary="Edit a draft")
async def edit_document(
    document_id: int,
    payload: DocumentEditRequest,
    session: AsyncSession = Depends(get_session),
    user: UserRecord = Depends(require_officer),
) -> DocumentDetail:
    if not has_permission(user.role, Permission.DOCUMENT_DRAFT):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your role may not edit documents.")
    document = await _document_or_404(session, document_id, user)
    try:
        await workflow_service.edit(session, document, user, body_html=payload.body_html)
    except workflow_service.WorkflowError as error:
        raise _handle(error) from error
    return to_detail(document, document.case.case_id)


# --- transitions ------------------------------------------------------------


async def _transition(session, document_id, user, action, **kwargs) -> DocumentDetail:
    document = await _document_or_404(session, document_id, user)
    try:
        await action(session, document, user, **kwargs)
    except workflow_service.WorkflowError as error:
        raise _handle(error) from error
    await session.refresh(document)
    document = await _document_or_404(session, document_id, user)
    return to_detail(document, document.case.case_id)


@router.post("/documents/{document_id}/submit", response_model=DocumentDetail, summary="Send for approval")
async def submit_document(
    document_id: int,
    session: AsyncSession = Depends(get_session),
    user: UserRecord = Depends(require_officer),
) -> DocumentDetail:
    return await _transition(session, document_id, user, workflow_service.submit)


@router.post("/documents/{document_id}/approve", response_model=DocumentDetail, summary="Approve at your stage")
async def approve_document(
    document_id: int,
    payload: DocumentCommentRequest | None = None,
    session: AsyncSession = Depends(get_session),
    user: UserRecord = Depends(require_officer),
) -> DocumentDetail:
    return await _transition(
        session, document_id, user, workflow_service.approve, comment=(payload.comment if payload else None)
    )


@router.post("/documents/{document_id}/return", response_model=DocumentDetail, summary="Return for correction")
async def return_document(
    document_id: int,
    payload: DocumentReturnRequest,
    session: AsyncSession = Depends(get_session),
    user: UserRecord = Depends(require_officer),
) -> DocumentDetail:
    return await _transition(session, document_id, user, workflow_service.send_back, comment=payload.comment)


@router.post("/documents/{document_id}/dispatch", response_model=DocumentDetail, summary="Record dispatch")
async def dispatch_document(
    document_id: int,
    payload: DocumentDispatchRequest,
    session: AsyncSession = Depends(get_session),
    user: UserRecord = Depends(require_officer),
) -> DocumentDetail:
    return await _transition(
        session,
        document_id,
        user,
        workflow_service.dispatch,
        channel=payload.channel.value,
        reference=payload.reference,
    )


@router.post("/documents/{document_id}/response", response_model=DocumentDetail, summary="Record a reply")
async def record_response(
    document_id: int,
    payload: DocumentResponseRequest,
    session: AsyncSession = Depends(get_session),
    user: UserRecord = Depends(require_officer),
) -> DocumentDetail:
    return await _transition(session, document_id, user, workflow_service.record_response, note=payload.note)


@router.post("/documents/{document_id}/close", response_model=DocumentDetail, summary="Close the requisition")
async def close_document(
    document_id: int,
    session: AsyncSession = Depends(get_session),
    user: UserRecord = Depends(require_officer),
) -> DocumentDetail:
    return await _transition(session, document_id, user, workflow_service.close)


@router.post("/documents/{document_id}/cancel", response_model=DocumentDetail, summary="Cancel with a reason")
async def cancel_document(
    document_id: int,
    payload: DocumentReturnRequest,
    session: AsyncSession = Depends(get_session),
    user: UserRecord = Depends(require_officer),
) -> DocumentDetail:
    return await _transition(session, document_id, user, workflow_service.cancel, reason=payload.comment)


# --- queue and MIS ----------------------------------------------------------


@router.get("/queue", response_model=QueueResponse, summary="What is waiting for me")
async def my_queue(
    session: AsyncSession = Depends(get_session),
    user: UserRecord = Depends(require_officer),
    limit: int = Query(default=50, ge=1, le=200),
) -> QueueResponse:
    documents = await workflow_service.pending_for(session, user, limit=limit)
    summaries = []
    for document in documents:
        case = (
            await session.execute(select(CaseRecord).where(CaseRecord.id == document.case_id))
        ).scalar_one_or_none()
        summaries.append(to_summary(document, case.case_id if case else ""))
    summaries.sort(key=lambda item: (not item.overdue, item.due_at or ""))
    return QueueResponse(
        stage=user.role,
        total=len(summaries),
        overdue=sum(1 for item in summaries if item.overdue),
        documents=summaries,
    )


@router.get("/reports/mis", response_model=MisReport, summary="Numbers for the senior officer")
async def mis_report(
    period: str = Query(default="weekly", pattern="^(daily|weekly|monthly)$"),
    session: AsyncSession = Depends(get_session),
    user: UserRecord = Depends(require_officer),
) -> MisReport:
    return await mis_service.build_report(session, user=user, period=period)


__all__ = ["router", "to_detail", "to_summary"]
