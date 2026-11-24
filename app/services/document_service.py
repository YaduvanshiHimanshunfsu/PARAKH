from __future__ import annotations

"""Generate an action pack from a case (planversionalpha.md D.4).

The whole point of Phase D: an officer who has a case should not have to type
five notices by hand. PARAKH groups the case's suspect identifiers by
(document type, addressee) so two UPI IDs on the same provider produce **one**
notice naming both, drafts each one, and leaves every draft unsigned and
unsent until the chain of command approves it.

Regenerating is idempotent: groups that already have a live document are
skipped rather than duplicated.
"""

import hashlib
import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.approval_policy import first_stage, policy_for
from app.db.models import CaseRecord, DocumentRecord, DocumentVersionRecord, UnitRecord, UserRecord
from app.schemas import CaseDetail, Identifier, IdentifierType
from app.services import addressee_resolver, case_service, document_templates
from app.services.addressee_resolver import BSA_63_CERT, Resolution
from app.services.identifier_roles import LINKING_ROLES

logger = logging.getLogger(__name__)

# Statuses that mean a document still exists for this group, so regenerating
# must not create a second one.
LIVE_STATUSES = ("DRAFT", "RETURNED", "PENDING_STATION", "PENDING_SUPERVISOR", "APPROVED", "DISPATCHED", "RESPONDED")

ROLE_VALUES = {role.value for role in LINKING_ROLES}


def body_hash(html: str) -> str:
    return hashlib.sha256(html.encode("utf-8")).hexdigest()


async def _next_doc_no(session: AsyncSession, unit_code: str) -> str:
    """Readable office number: PRK/<unit>/<year>/<serial>."""

    year = datetime.now(timezone.utc).year
    prefix = f"PRK/{unit_code}/{year}/"
    used = (
        await session.execute(
            select(func.count(DocumentRecord.id)).where(DocumentRecord.doc_no.startswith(prefix))
        )
    ).scalar_one()
    return f"{prefix}{used + 1:04d}"


def _officer_block(user: UserRecord | None, unit: UnitRecord | None) -> dict:
    return {
        "username": getattr(user, "username", ""),
        "display_name": getattr(user, "display_name", None) or getattr(user, "username", ""),
        "rank": getattr(user, "rank", None) or "",
        "unit": getattr(unit, "name", None) or "",
    }


def _identifier_payload(resolutions: list[Resolution]) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    payload: list[dict] = []
    for resolution in resolutions:
        identifier = resolution.identifier
        key = (identifier.type.value, identifier.value)
        if key in seen:
            continue
        seen.add(key)
        payload.append(
            {
                "type": identifier.type.value,
                "value": identifier.value,
                "context": (identifier.context or "")[:200],
            }
        )
    return payload


def plan_action_pack(detail: CaseDetail) -> dict[tuple[str, str], list[Resolution]]:
    """Group the case's actionable identifiers into one requisition each."""

    actionable = [
        item
        for item in detail.identifiers
        # Only the other side of the fraud: a victim's own number and an
        # impersonated brand's domain must never be served a notice (B.6).
        if (item.role or "UNKNOWN") in ROLE_VALUES
    ]
    groups: dict[tuple[str, str], list[Resolution]] = {}
    for resolution in addressee_resolver.resolve_all(actionable):
        groups.setdefault(resolution.group_key, []).append(resolution)
    return groups


async def generate_action_pack(
    session: AsyncSession,
    case: CaseRecord,
    *,
    user: UserRecord | None,
    unit: UnitRecord | None = None,
) -> list[DocumentRecord]:
    """Draft every requisition this case justifies. Safe to call again."""

    detail = case_service.to_detail(case)
    groups = plan_action_pack(detail)

    existing = {
        (row.doc_type, row.addressee_key)
        for row in (
            await session.execute(
                select(DocumentRecord).where(
                    DocumentRecord.case_id == case.id,
                    DocumentRecord.status.in_(LIVE_STATUSES),
                )
            )
        )
        .scalars()
        .all()
    }

    unit_code = getattr(unit, "code", None) or "RJ"
    unit_name = getattr(unit, "name", None) or "Cyber Police Station"
    officer = _officer_block(user, unit)
    created: list[DocumentRecord] = []

    for (doc_type, addressee_key), resolutions in sorted(groups.items()):
        if (doc_type, addressee_key) in existing:
            continue
        created.append(
            await _create_document(
                session,
                case=case,
                detail=detail,
                doc_type=doc_type,
                resolutions=resolutions,
                unit_code=unit_code,
                unit_name=unit_name,
                officer=officer,
                user=user,
            )
        )

    # A certificate for the electronic evidence is always drafted: every case
    # that reaches court needs one, and it is the step most often forgotten.
    if (BSA_63_CERT, "internal.record") not in existing:
        created.append(
            await _create_document(
                session,
                case=case,
                detail=detail,
                doc_type=BSA_63_CERT,
                resolutions=[],
                unit_code=unit_code,
                unit_name=unit_name,
                officer=officer,
                user=user,
            )
        )

    logger.info("action_pack_generated case_id=%s documents=%d", case.case_id, len(created))
    return created


async def _create_document(
    session: AsyncSession,
    *,
    case: CaseRecord,
    detail: CaseDetail,
    doc_type: str,
    resolutions: list[Resolution],
    unit_code: str,
    unit_name: str,
    officer: dict,
    user: UserRecord | None,
) -> DocumentRecord:
    from app.data.addressees import get as get_addressee

    addressee = resolutions[0].addressee if resolutions else get_addressee("internal.record")
    identifiers = _identifier_payload(resolutions)
    notes = [resolution.note for resolution in resolutions]

    doc_no = await _next_doc_no(session, unit_code)
    html = document_templates.render(
        doc_type=doc_type,
        doc_no=doc_no,
        detail=detail,
        unit_name=unit_name,
        officer=officer,
        addressee_display=addressee.org_name,
        addressee_contact=addressee.contact_placeholder,
        addressee_is_sample=addressee.is_sample,
        identifiers=identifiers,
        resolution_notes=notes,
        approved=False,
    )

    document = DocumentRecord(
        doc_no=doc_no,
        case_id=case.id,
        doc_type=doc_type,
        addressee_key=addressee.key,
        addressee_display=addressee.org_name,
        addressee_is_sample=addressee.is_sample,
        subject_identifiers=identifiers,
        status="DRAFT",
        current_stage=first_stage(doc_type, case.amount_lost),
        version=1,
        body_html=html,
        body_sha256=body_hash(html),
        unit_path=case.unit_path or "/",
        created_by=getattr(user, "id", None),
    )
    session.add(document)
    await session.flush()
    session.add(
        DocumentVersionRecord(
            document_id=document.id,
            version=1,
            body_html=html,
            body_sha256=document.body_sha256,
            edited_by=getattr(user, "id", None),
        )
    )
    await session.flush()
    return document


def describe(doc_type: str) -> dict:
    policy = policy_for(doc_type)
    return {
        "doc_type": policy.doc_type,
        "title": policy.title,
        "legal_basis": policy.legal_basis,
        "purpose": policy.purpose,
        "sla_hours": policy.sla_hours,
    }


__all__ = ["body_hash", "describe", "generate_action_pack", "plan_action_pack"]
