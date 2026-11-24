from __future__ import annotations

"""Classify what an identifier *is* in a case (planversionalpha.md B.6).

The victim's own number, the bank helpline a scammer impersonates and the
scammer's UPI ID all used to be stored identically, so the heat-list and the
case-linking graph treated a bank's real helpline as a shared criminal asset.

Roles, in the order they are decided (first match wins):

``OFFICIAL_CONTACT``
    A real helpline or official domain. Never links cases, never heat-listed.
``IMPERSONATED_BRAND``
    A protected brand's own namespace appearing in a fraud case: evidence of
    impersonation, not of a shared operator.
``VICTIM``
    The complainant's own identifier, named as theirs in the reporter note.
``SUSPECT``
    The identifier the message tells the reader to pay, call or join.
``UNKNOWN``
    Everything else. Treated as possibly-suspect for linking, because most
    identifiers in a scam message belong to the operator.

Only ``SUSPECT`` and ``UNKNOWN`` feed linking, campaigns and the heat-list.
"""

import re
from enum import Enum

from app.data.protected_brands import is_official_domain
from app.data.trusted_channels import TRUSTED_CHANNELS
from app.schemas import Identifier, IdentifierType


class IdentifierRole(str, Enum):
    SUSPECT = "SUSPECT"
    VICTIM = "VICTIM"
    IMPERSONATED_BRAND = "IMPERSONATED_BRAND"
    OFFICIAL_CONTACT = "OFFICIAL_CONTACT"
    UNKNOWN = "UNKNOWN"


# Roles that represent the other side of the fraud and may link cases.
LINKING_ROLES = frozenset({IdentifierRole.SUSPECT, IdentifierRole.UNKNOWN})

_CONTEXT = 60

# "pay this", "call this", "join this" - an instruction aimed at the reader.
_SUSPECT_CONTEXT = re.compile(
    r"(?:pay|send|transfer|deposit|remit|credit|call|whatsapp|contact|join|msg|message|ping|scan|"
    r"bhej|bhejo|jama|karo\s+call|"
    r"भेज|जमा|कॉल|संपर्क|जुड)",
    re.IGNORECASE,
)

# "my number", "mera account" - the complainant describing their own details.
_VICTIM_CONTEXT = re.compile(
    r"(?:\bmy\b|\bmine\b|\bi\s+(?:use|have|own)\b|\bvictim(?:'s)?\b|\bcomplainant(?:'s)?\b|"
    r"\bmera\b|\bmeri\b|\bapna\b|"
    r"मेर[ाीे]|पीड़ित)",
    re.IGNORECASE,
)

_PHONE_TYPES = {IdentifierType.PHONE}
_HOST_TYPES = {IdentifierType.DOMAIN, IdentifierType.URL, IdentifierType.EMAIL}


# Reviewed public helplines and short codes. A number here is a destination a
# citizen should call, never a scammer's contact, so it must not be heat-listed.
PUBLIC_HELPLINES: tuple[str, ...] = (
    "1930",   # National Cyber Crime Helpline
    "112",    # Emergency Response Support System
    "1091",   # Women helpline
    "1098",   # Childline
    "1912",   # Electricity complaints
    "1800111109",  # UIDAI Aadhaar helpline
    "18001801290",  # Rajasthan Sampark
    "14416",  # Tele-MANAS mental health
    "155260",  # earlier cyber financial fraud helpline
)


def _official_numbers() -> frozenset[str]:
    numbers = {re.sub(r"\D", "", number) for number in PUBLIC_HELPLINES}
    for channel in TRUSTED_CHANNELS:
        if channel.phone:
            digits = re.sub(r"\D", "", channel.phone)
            if digits:
                numbers.add(digits)
    return frozenset(numbers)


OFFICIAL_NUMBERS = _official_numbers()


def _host_of(value: str) -> str:
    host = re.sub(r"^[a-z]+://", "", value.strip().lower())
    host = host.split("/", 1)[0].split("?", 1)[0].split(":", 1)[0]
    if "@" in host:
        host = host.rsplit("@", 1)[1]
    return host.removeprefix("www.")


def is_official_contact(identifier: Identifier) -> bool:
    if identifier.type in _PHONE_TYPES:
        digits = re.sub(r"\D", "", identifier.value)
        # Short codes such as 1930, 1912 and 112 reach the extractor with the
        # country code attached, so compare the bare number too. lstrip() is
        # wrong here: it would eat every leading 9 and 1 of "911930".
        candidates = {digits, digits.removeprefix("91"), digits.lstrip("0")}
        return bool(candidates & OFFICIAL_NUMBERS)
    if identifier.type in _HOST_TYPES:
        return is_official_domain(_host_of(identifier.value))
    return False


def classify(identifier: Identifier, *, reporter_note: str | None = None, officer_role: str | None = None) -> IdentifierRole:
    """Decide the role of one identifier. An officer's choice always wins."""

    if officer_role:
        try:
            return IdentifierRole(officer_role)
        except ValueError:
            pass

    if is_official_contact(identifier):
        # A protected brand's own namespace inside a fraud case is evidence of
        # impersonation; a helpline is simply an official contact.
        if identifier.type in _HOST_TYPES:
            return IdentifierRole.IMPERSONATED_BRAND
        return IdentifierRole.OFFICIAL_CONTACT

    note = reporter_note or ""
    if note and _mentions_as_own(note, identifier.value):
        return IdentifierRole.VICTIM

    context = identifier.context or ""
    if context and _VICTIM_CONTEXT.search(context):
        return IdentifierRole.VICTIM
    if context and _SUSPECT_CONTEXT.search(context):
        return IdentifierRole.SUSPECT
    return IdentifierRole.UNKNOWN


def _mentions_as_own(note: str, value: str) -> bool:
    """The reporter note names this identifier as the complainant's own."""

    tail = re.sub(r"\D", "", value)[-10:]
    needle = tail if tail else value.lower()
    position = note.lower().find(needle.lower())
    if position < 0:
        return False
    window = note[max(0, position - _CONTEXT): position + len(needle) + 20]
    return bool(_VICTIM_CONTEXT.search(window))


def classify_all(
    identifiers: list[Identifier], *, reporter_note: str | None = None
) -> dict[tuple[IdentifierType, str], IdentifierRole]:
    return {
        (item.type, item.value): classify(item, reporter_note=reporter_note) for item in identifiers
    }


def links_cases_with_role(role: str | None) -> bool:
    """Whether an identifier in this role may link two cases together."""

    if not role:
        return True
    try:
        return IdentifierRole(role) in LINKING_ROLES
    except ValueError:
        return True


__all__ = [
    "IdentifierRole",
    "LINKING_ROLES",
    "OFFICIAL_NUMBERS",
    "classify",
    "classify_all",
    "is_official_contact",
    "links_cases_with_role",
]
