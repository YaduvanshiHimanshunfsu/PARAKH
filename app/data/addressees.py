from __future__ import annotations

"""Who a legal requisition is addressed to (planversionalpha.md D.2).

Two honesty rules govern this file:

* **No invented contact details.** A nodal officer's email or phone is not
  guessed. Entries carry a placeholder and ``is_sample=True``, and the UI
  shows a "sample contact - replace with the official nodal contact" badge.
  The officer fills in the real address from their own directory.
* **Mappings that change are marked to verify.** UPI handle to sponsor bank
  partnerships are commercial arrangements that change; an IFSC prefix is
  stable. Both are shown, but the first says "confirm before dispatch".

Real contacts are expected to be loaded per deployment from the force's own
nodal-officer directory, which is not public and is not shipped here.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Addressee:
    key: str
    org_name: str
    org_type: str  # BANK | PSP | TELECOM | REGISTRAR | HOSTING | PLATFORM | DOT | COURT
    channel: str   # EMAIL | PORTAL | POST
    contact_placeholder: str
    notes: str = ""
    is_sample: bool = True


def _bank(key: str, name: str) -> Addressee:
    return Addressee(
        key=key,
        org_name=name,
        org_type="BANK",
        channel="EMAIL",
        contact_placeholder="Nodal Officer (Law Enforcement) - address from the force directory",
        notes="Banks publish a nodal officer for law-enforcement requests; use the current one.",
    )


BANKS: tuple[Addressee, ...] = (
    _bank("bank.sbi", "State Bank of India"),
    _bank("bank.hdfc", "HDFC Bank"),
    _bank("bank.icici", "ICICI Bank"),
    _bank("bank.axis", "Axis Bank"),
    _bank("bank.kotak", "Kotak Mahindra Bank"),
    _bank("bank.pnb", "Punjab National Bank"),
    _bank("bank.bob", "Bank of Baroda"),
    _bank("bank.canara", "Canara Bank"),
    _bank("bank.union", "Union Bank of India"),
    _bank("bank.idfc", "IDFC First Bank"),
    _bank("bank.yes", "Yes Bank"),
    _bank("bank.indusind", "IndusInd Bank"),
    _bank("bank.rmgb", "Rajasthan Marudhara Gramin Bank"),
    _bank("bank.unknown", "the account-holding bank"),
)

PSPS: tuple[Addressee, ...] = (
    Addressee("psp.phonepe", "PhonePe Payments", "PSP", "EMAIL", "Nodal Officer (Law Enforcement)"),
    Addressee("psp.googlepay", "Google Pay India", "PSP", "EMAIL", "Nodal Officer (Law Enforcement)"),
    Addressee("psp.paytm", "Paytm Payments Bank / One97", "PSP", "EMAIL", "Nodal Officer (Law Enforcement)"),
    Addressee("psp.amazonpay", "Amazon Pay India", "PSP", "EMAIL", "Nodal Officer (Law Enforcement)"),
    Addressee("psp.bhim", "NPCI (BHIM UPI)", "PSP", "EMAIL", "Nodal Officer (Law Enforcement)"),
    Addressee("psp.unknown", "the payment service provider", "PSP", "EMAIL", "Nodal Officer (Law Enforcement)"),
)

TELECOM: tuple[Addressee, ...] = (
    Addressee("telecom.airtel", "Bharti Airtel", "TELECOM", "EMAIL", "Nodal Officer (Law Enforcement)"),
    Addressee("telecom.jio", "Reliance Jio", "TELECOM", "EMAIL", "Nodal Officer (Law Enforcement)"),
    Addressee("telecom.vi", "Vodafone Idea", "TELECOM", "EMAIL", "Nodal Officer (Law Enforcement)"),
    Addressee("telecom.bsnl", "BSNL", "TELECOM", "EMAIL", "Nodal Officer (Law Enforcement)"),
    Addressee("telecom.unknown", "the telecom service provider", "TELECOM", "EMAIL", "Nodal Officer (Law Enforcement)"),
)

PLATFORMS: tuple[Addressee, ...] = (
    Addressee(
        "platform.telegram", "Telegram FZ-LLC", "PLATFORM", "PORTAL",
        "Submitted through the Sahyog portal (MHA)",
        notes="Intermediary notices under IT Act s.79(3)(b) are routed through Sahyog.",
    ),
    Addressee(
        "platform.whatsapp", "WhatsApp LLC (Meta)", "PLATFORM", "PORTAL",
        "Submitted through the Sahyog portal (MHA)",
    ),
    Addressee(
        "platform.google_play", "Google Play (app takedown)", "PLATFORM", "PORTAL",
        "Google Play law-enforcement request portal",
    ),
    Addressee(
        "platform.unknown", "the intermediary", "PLATFORM", "PORTAL",
        "Submitted through the Sahyog portal (MHA)",
    ),
)

OTHERS: tuple[Addressee, ...] = (
    Addressee(
        "registrar.unknown", "the domain registrar", "REGISTRAR", "EMAIL",
        "Registrar abuse contact from the RDAP record",
        notes="The abuse address is read from RDAP, not guessed.",
    ),
    Addressee(
        "hosting.unknown", "the hosting provider", "HOSTING", "EMAIL",
        "Network abuse contact from the RDAP record",
    ),
    Addressee(
        "dot.chakshu", "Department of Telecommunications (Sanchar Saathi / Chakshu)", "DOT", "PORTAL",
        "Reported on sancharsaathi.gov.in",
        notes="Citizen and police reporting of fraud numbers.",
    ),
    Addressee(
        "internal.record", "Case record (internal)", "COURT", "POST",
        "Filed with the case diary",
        notes="Not dispatched outside the force.",
        is_sample=False,
    ),
)

ALL_ADDRESSEES: tuple[Addressee, ...] = BANKS + PSPS + TELECOM + PLATFORMS + OTHERS
BY_KEY: dict[str, Addressee] = {item.key: item for item in ALL_ADDRESSEES}

# UPI handle -> (PSP key, sponsor bank key). These partnerships change, so
# every entry is shown to the officer as "confirm before dispatch".
UPI_HANDLE_MAP: dict[str, tuple[str, str]] = {
    "ybl": ("psp.phonepe", "bank.yes"),
    "ibl": ("psp.phonepe", "bank.idfc"),
    "axl": ("psp.phonepe", "bank.axis"),
    "okaxis": ("psp.googlepay", "bank.axis"),
    "okhdfcbank": ("psp.googlepay", "bank.hdfc"),
    "oksbi": ("psp.googlepay", "bank.sbi"),
    "okicici": ("psp.googlepay", "bank.icici"),
    "paytm": ("psp.paytm", "bank.unknown"),
    "ptyes": ("psp.paytm", "bank.yes"),
    "ptaxis": ("psp.paytm", "bank.axis"),
    "apl": ("psp.amazonpay", "bank.unknown"),
    "yapl": ("psp.amazonpay", "bank.yes"),
    "rapl": ("psp.amazonpay", "bank.unknown"),
    "upi": ("psp.bhim", "bank.unknown"),
    "sbi": ("psp.unknown", "bank.sbi"),
    "hdfcbank": ("psp.unknown", "bank.hdfc"),
    "icici": ("psp.unknown", "bank.icici"),
    "axisbank": ("psp.unknown", "bank.axis"),
    "kotak": ("psp.unknown", "bank.kotak"),
    "pnb": ("psp.unknown", "bank.pnb"),
    "barodampay": ("psp.unknown", "bank.bob"),
    "cnrb": ("psp.unknown", "bank.canara"),
    "uboi": ("psp.unknown", "bank.union"),
    "indus": ("psp.unknown", "bank.indusind"),
}

# IFSC prefix -> bank key. Stable: the prefix is allocated with the bank.
IFSC_BANK_MAP: dict[str, str] = {
    "SBIN": "bank.sbi",
    "HDFC": "bank.hdfc",
    "ICIC": "bank.icici",
    "UTIB": "bank.axis",
    "KKBK": "bank.kotak",
    "PUNB": "bank.pnb",
    "BARB": "bank.bob",
    "CNRB": "bank.canara",
    "UBIN": "bank.union",
    "IDFB": "bank.idfc",
    "YESB": "bank.yes",
    "INDB": "bank.indusind",
    "RMGB": "bank.rmgb",
}

# Telecom operator name (as libphonenumber reports it) -> addressee key.
CARRIER_MAP: dict[str, str] = {
    "airtel": "telecom.airtel",
    "bharti": "telecom.airtel",
    "jio": "telecom.jio",
    "reliance": "telecom.jio",
    "vodafone": "telecom.vi",
    "idea": "telecom.vi",
    "vi": "telecom.vi",
    "bsnl": "telecom.bsnl",
    "mtnl": "telecom.bsnl",
}


def get(key: str) -> Addressee:
    return BY_KEY.get(key, BY_KEY["bank.unknown"])


__all__ = [
    "Addressee",
    "ALL_ADDRESSEES",
    "BY_KEY",
    "CARRIER_MAP",
    "IFSC_BANK_MAP",
    "UPI_HANDLE_MAP",
    "get",
]
