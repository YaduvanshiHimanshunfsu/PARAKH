from __future__ import annotations

"""Decide who each identifier's requisition should go to (planversionalpha.md D.2).

The resolver never invents a contact. It names the organisation and says how
confident it is about that mapping:

* an IFSC prefix is allocated with the bank, so that mapping is ``CONFIRMED``;
* a UPI handle's sponsor bank is a commercial arrangement that changes, and a
  mobile number may have been ported, so those are ``VERIFY`` and the drafted
  notice carries a visible "confirm before dispatch" line.

Anything it cannot resolve becomes a generic addressee the officer completes,
rather than a wrong one stated confidently.
"""

import logging
import re
from dataclasses import dataclass

from app.data.addressees import (
    CARRIER_MAP,
    IFSC_BANK_MAP,
    UPI_HANDLE_MAP,
    Addressee,
    get,
)
from app.schemas import Identifier, IdentifierType

logger = logging.getLogger(__name__)

# Document types a resolved identifier can justify.
BANK_PRODUCE_94 = "BANK_PRODUCE_94"
BANK_FREEZE_106 = "BANK_FREEZE_106"
TELECOM_CAF_CDR = "TELECOM_CAF_CDR"
DOT_CHAKSHU_REPORT = "DOT_CHAKSHU_REPORT"
REGISTRAR_TAKEDOWN = "REGISTRAR_TAKEDOWN"
HOSTING_ABUSE = "HOSTING_ABUSE"
INTERMEDIARY_79_3B = "INTERMEDIARY_79_3B"
BSA_63_CERT = "BSA_63_CERT"

CONFIRMED = "CONFIRMED"
VERIFY = "VERIFY"
UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class Resolution:
    """One identifier mapped to an addressee and the notice it justifies."""

    identifier: Identifier
    doc_type: str
    addressee: Addressee
    confidence: str
    note: str = ""

    @property
    def group_key(self) -> tuple[str, str]:
        """Identifiers sharing this key go into one notice."""

        return (self.doc_type, self.addressee.key)


def _upi_handle(value: str) -> str:
    return value.rsplit("@", 1)[1].lower() if "@" in value else ""


def resolve(identifier: Identifier) -> list[Resolution]:
    """Every requisition this one identifier justifies."""

    kind = identifier.type
    value = identifier.value

    if kind is IdentifierType.UPI:
        handle = _upi_handle(value)
        mapping = UPI_HANDLE_MAP.get(handle)
        if mapping is None:
            return [
                Resolution(
                    identifier, BANK_PRODUCE_94, get("psp.unknown"), UNRESOLVED,
                    f"The UPI handle '@{handle}' is not in PARAKH's reviewed list. "
                    "Identify the payment service provider before dispatch.",
                )
            ]
        psp_key, bank_key = mapping
        psp = get(psp_key)
        note = (
            f"'@{handle}' is mapped to {psp.org_name}"
            + (f", sponsor bank {get(bank_key).org_name}" if bank_key != "bank.unknown" else "")
            + ". Handle-to-bank arrangements change; confirm before dispatch."
        )
        # Both a production notice and a freeze request: the money moves fast,
        # so the officer should have both drafts ready to submit.
        return [
            Resolution(identifier, BANK_PRODUCE_94, psp, VERIFY, note),
            Resolution(identifier, BANK_FREEZE_106, psp, VERIFY, note),
        ]

    if kind is IdentifierType.IFSC:
        prefix = value[:4].upper()
        bank = get(IFSC_BANK_MAP.get(prefix, "bank.unknown"))
        confidence = CONFIRMED if prefix in IFSC_BANK_MAP else UNRESOLVED
        return [
            Resolution(
                identifier, BANK_PRODUCE_94, bank, confidence,
                f"IFSC prefix {prefix} is allocated to {bank.org_name}."
                if confidence == CONFIRMED
                else f"IFSC prefix {prefix} is not in PARAKH's reviewed list.",
            )
        ]

    if kind is IdentifierType.BANK_ACCOUNT:
        return [
            Resolution(
                identifier, BANK_PRODUCE_94, get("bank.unknown"), UNRESOLVED,
                "The account number alone does not identify the bank. Add the IFSC from the "
                "victim's transaction record before dispatch.",
            ),
            Resolution(
                identifier, BANK_FREEZE_106, get("bank.unknown"), UNRESOLVED,
                "Add the IFSC before dispatch.",
            ),
        ]

    if kind is IdentifierType.PHONE:
        operator, confidence = _carrier_for(value)
        note = (
            f"{operator.org_name} was the originally allocated operator. The number may have "
            "been ported (MNP); confirm the current operator before dispatch."
            if confidence != UNRESOLVED
            else "The operator could not be determined offline. Confirm before dispatch."
        )
        return [
            Resolution(identifier, TELECOM_CAF_CDR, operator, confidence, note),
            Resolution(
                identifier, DOT_CHAKSHU_REPORT, get("dot.chakshu"), CONFIRMED,
                "Reporting a fraud number on Sanchar Saathi / Chakshu is a public channel.",
            ),
        ]

    if kind in {IdentifierType.DOMAIN, IdentifierType.URL}:
        return [
            Resolution(
                identifier, REGISTRAR_TAKEDOWN, get("registrar.unknown"), UNRESOLVED,
                "The registrar and its abuse contact come from the domain's RDAP record. "
                "Fetch the RDAP record and fill in the registrar before dispatch.",
            )
        ]

    if kind is IdentifierType.IP:
        return [
            Resolution(
                identifier, HOSTING_ABUSE, get("hosting.unknown"), UNRESOLVED,
                "The network owner and abuse contact come from the IP's RDAP record.",
            )
        ]

    if kind in {IdentifierType.TELEGRAM, IdentifierType.TELEGRAM_BOT}:
        return [
            Resolution(
                identifier, INTERMEDIARY_79_3B, get("platform.telegram"), CONFIRMED,
                "Intermediary notices are routed through the Sahyog portal.",
            )
        ]

    if kind is IdentifierType.PACKAGE:
        return [
            Resolution(
                identifier, INTERMEDIARY_79_3B, get("platform.google_play"), CONFIRMED,
                "App takedown requests go through the Google Play law-enforcement portal.",
            )
        ]

    return []


def _carrier_for(value: str) -> tuple[Addressee, str]:
    """Originally allocated operator for an Indian mobile number."""

    digits = re.sub(r"\D", "", value)
    if not digits:
        return get("telecom.unknown"), UNRESOLVED
    try:
        import phonenumbers
        from phonenumbers import carrier

        parsed = phonenumbers.parse(value if value.startswith("+") else f"+{digits}", "IN")
        name = (carrier.name_for_number(parsed, "en") or "").lower()
    except Exception as exc:  # pragma: no cover - library is defensive
        logger.info("carrier_lookup_failed error=%s", type(exc).__name__)
        return get("telecom.unknown"), UNRESOLVED

    for needle, key in CARRIER_MAP.items():
        if needle in name:
            return get(key), VERIFY
    return get("telecom.unknown"), UNRESOLVED


def resolve_all(identifiers: list[Identifier]) -> list[Resolution]:
    out: list[Resolution] = []
    for identifier in identifiers:
        out.extend(resolve(identifier))
    return out


__all__ = [
    "BANK_FREEZE_106",
    "BANK_PRODUCE_94",
    "BSA_63_CERT",
    "CONFIRMED",
    "DOT_CHAKSHU_REPORT",
    "HOSTING_ABUSE",
    "INTERMEDIARY_79_3B",
    "REGISTRAR_TAKEDOWN",
    "Resolution",
    "TELECOM_CAF_CDR",
    "UNRESOLVED",
    "VERIFY",
    "resolve",
    "resolve_all",
]
