from __future__ import annotations

"""Which documents need whose approval, and how long each stage may take.

Policy, not code: a force can change these without touching the workflow
engine (planversionalpha.md D.5). The SLA drives escalation, which is computed
on read (``now > due_at``) so no scheduler is needed for the demo.
"""

from dataclasses import dataclass

from app.services.addressee_resolver import (
    BANK_FREEZE_106,
    BANK_PRODUCE_94,
    BSA_63_CERT,
    DOT_CHAKSHU_REPORT,
    HOSTING_ABUSE,
    INTERMEDIARY_79_3B,
    REGISTRAR_TAKEDOWN,
    TELECOM_CAF_CDR,
)

STAGE_STATION = "STATION"
STAGE_SUPERVISOR = "SUPERVISOR"
STAGE_NONE = "NONE"


@dataclass(frozen=True)
class DocumentPolicy:
    doc_type: str
    title: str
    legal_basis: str
    station_approval: bool
    supervisor_approval: bool
    # Supervisor approval is also required above this loss, in paise.
    supervisor_above_paise: int | None
    sla_hours: float
    purpose: str


_TEN_LAKH_PAISE = 10_00_000 * 100

POLICIES: tuple[DocumentPolicy, ...] = (
    DocumentPolicy(
        BANK_FREEZE_106,
        "Request to hold disputed funds",
        "Section 106, Bharatiya Nagarik Suraksha Sanhita, 2023",
        station_approval=True,
        supervisor_approval=True,
        supervisor_above_paise=None,
        # The golden hour: a freeze request that waits a day is usually too late.
        sla_hours=2,
        purpose="Ask the bank or PSP to hold the disputed amount in the suspect account.",
    ),
    DocumentPolicy(
        BANK_PRODUCE_94,
        "Notice to produce documents",
        "Section 94, Bharatiya Nagarik Suraksha Sanhita, 2023",
        station_approval=True,
        supervisor_approval=False,
        supervisor_above_paise=_TEN_LAKH_PAISE,
        sla_hours=24,
        purpose="Obtain KYC, statements, linked accounts and device or IP logs.",
    ),
    DocumentPolicy(
        TELECOM_CAF_CDR,
        "Notice to produce subscriber and call records",
        "Section 94, Bharatiya Nagarik Suraksha Sanhita, 2023",
        station_approval=True,
        supervisor_approval=False,
        supervisor_above_paise=None,
        sla_hours=24,
        purpose="Obtain the customer application form, call detail records and linked IMEI.",
    ),
    DocumentPolicy(
        DOT_CHAKSHU_REPORT,
        "Fraud number report (Sanchar Saathi / Chakshu)",
        "Department of Telecommunications public reporting channel",
        station_approval=True,
        supervisor_approval=False,
        supervisor_above_paise=None,
        sla_hours=24,
        purpose="Report the number so the connection can be examined for disconnection.",
    ),
    DocumentPolicy(
        REGISTRAR_TAKEDOWN,
        "Request to suspend a domain and disclose registrant details",
        "Section 79(3)(b), Information Technology Act, 2000",
        station_approval=True,
        supervisor_approval=True,
        supervisor_above_paise=None,
        sla_hours=24,
        purpose="Suspend the fraudulent website and obtain registrant and payment details.",
    ),
    DocumentPolicy(
        HOSTING_ABUSE,
        "Notice to a hosting provider",
        "Section 79(3)(b), Information Technology Act, 2000",
        station_approval=True,
        supervisor_approval=False,
        supervisor_above_paise=None,
        sla_hours=24,
        purpose="Remove the hosted content and preserve server logs.",
    ),
    DocumentPolicy(
        INTERMEDIARY_79_3B,
        "Intermediary takedown and disclosure notice",
        "Section 79(3)(b), Information Technology Act, 2000",
        station_approval=True,
        supervisor_approval=True,
        supervisor_above_paise=None,
        sla_hours=24,
        purpose="Remove the channel, group or app and disclose the operator's subscriber details.",
    ),
    DocumentPolicy(
        BSA_63_CERT,
        "Certificate for electronic evidence (Part A)",
        "Section 63, Bharatiya Sakshya Adhiniyam, 2023",
        station_approval=True,
        supervisor_approval=False,
        supervisor_above_paise=None,
        sla_hours=48,
        purpose="Certify how the electronic record was produced, for use in evidence.",
    ),
)

BY_TYPE: dict[str, DocumentPolicy] = {policy.doc_type: policy for policy in POLICIES}


def policy_for(doc_type: str) -> DocumentPolicy:
    policy = BY_TYPE.get(doc_type)
    if policy is None:
        raise KeyError(f"No approval policy for document type {doc_type!r}")
    return policy


def needs_supervisor(doc_type: str, amount_lost_paise: int | None) -> bool:
    """Whether this document must also reach a supervisor."""

    policy = policy_for(doc_type)
    if policy.supervisor_approval:
        return True
    threshold = policy.supervisor_above_paise
    return threshold is not None and (amount_lost_paise or 0) >= threshold


def first_stage(doc_type: str, amount_lost_paise: int | None = None) -> str:
    policy = policy_for(doc_type)
    if policy.station_approval:
        return STAGE_STATION
    return STAGE_SUPERVISOR if needs_supervisor(doc_type, amount_lost_paise) else STAGE_NONE


def next_stage(doc_type: str, current: str, amount_lost_paise: int | None = None) -> str:
    """The stage after ``current`` approves, or NONE when fully approved."""

    if current == STAGE_STATION and needs_supervisor(doc_type, amount_lost_paise):
        return STAGE_SUPERVISOR
    return STAGE_NONE


__all__ = [
    "BY_TYPE",
    "DocumentPolicy",
    "POLICIES",
    "STAGE_NONE",
    "STAGE_STATION",
    "STAGE_SUPERVISOR",
    "first_stage",
    "needs_supervisor",
    "next_stage",
    "policy_for",
]
