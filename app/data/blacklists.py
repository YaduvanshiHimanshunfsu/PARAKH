from __future__ import annotations

"""Seed entries for the reviewed blacklist.

Every entry records its source so a match is explainable in a report rather
than an unexplained verdict — PS01 requires the indicators behind a risk level,
not just the level.

The values below are **synthetic placeholders** for development and demo. Real
entries come from the R4C sample dataset and any public feed the team adopts.
Never commit identifiers belonging to real people.
"""

from dataclasses import dataclass

from app.schemas import IdentifierType


@dataclass(frozen=True)
class BlacklistSeed:
    type: IdentifierType
    value: str
    source: str
    reason: str


SEED_BLACKLIST: tuple[BlacklistSeed, ...] = (
    BlacklistSeed(
        IdentifierType.DOMAIN,
        "sbi-verify-kyc.in",
        "Demo dataset",
        "Reported repeatedly as an SBI KYC phishing host.",
    ),
    BlacklistSeed(
        IdentifierType.DOMAIN,
        "hdfc-kyc-update.xyz",
        "Demo dataset",
        "Look-alike HDFC credential-harvesting domain.",
    ),
    BlacklistSeed(
        IdentifierType.DOMAIN,
        "richplan-invest.xyz",
        "Demo dataset",
        "Ponzi investment site promising fixed daily returns.",
    ),
    BlacklistSeed(
        IdentifierType.DOMAIN,
        "quickcash-loan.top",
        "Demo dataset",
        "Distributes an unregulated instant-loan APK outside the Play Store.",
    ),
    BlacklistSeed(
        IdentifierType.UPI,
        "winner@ybl",
        "Demo dataset",
        "Collection account reused across lottery and Ponzi reports.",
    ),
    BlacklistSeed(
        IdentifierType.PHONE,
        "+919876543210",
        "Demo dataset",
        "Number reused across KYC and loan-recovery harassment reports.",
    ),
    BlacklistSeed(
        IdentifierType.PACKAGE,
        "com.quickloan.instant",
        "Demo dataset",
        "Loan app requesting SMS and contacts permissions with no RBI registration.",
    ),
)
