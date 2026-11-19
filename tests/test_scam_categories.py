from __future__ import annotations

"""Scam-category classification regression tests.

Two misclassifications were found only when seeded demo data was rendered in
the dashboard, not by any unit test:

* a plain courier scam was labelled ROMANCE_SCAM, because the romance rule
  matched a bare "parcel ... customs" with no relationship language at all;
* a fake-job scam was labelled LOTTERY_PRIZE, because "registration fee"
  carried the lottery category and outweighed the job rule.

Both are the same underlying mistake — a cross-cutting *tactic* claiming a
fraud *family*. These cases pin the corrected behaviour.
"""

import pytest

from app.schemas import ScamCategory, Verdict
from app.services.fallback_analyzer import RuleBasedFallbackAnalyzer


@pytest.fixture()
def analyzer() -> RuleBasedFallbackAnalyzer:
    return RuleBasedFallbackAnalyzer()


@pytest.mark.parametrize(
    "expected,message",
    [
        (
            ScamCategory.COURIER_SCAM,
            "Your parcel is held at customs. Pay clearance duty of Rs 2,450 within 12 hours "
            "to release it, or it will be returned.",
        ),
        (
            ScamCategory.FAKE_JOB,
            "Work from home! Earn Rs 800-1500 per hour by liking YouTube videos. "
            "Registration fee Rs 500 only.",
        ),
        (
            ScamCategory.ROMANCE_SCAM,
            "My love, I have sent you a gift parcel but customs is asking for a fee of "
            "15000 to release it.",
        ),
        (
            ScamCategory.LOTTERY_PRIZE,
            "Congratulations! You won KBC lottery of 25 lakh. Pay processing fee to claim prize.",
        ),
        (
            ScamCategory.LOAN_APP_FRAUD,
            "Instant loan in 5 minutes! No CIBIL check, only Aadhaar. Download quickcash.apk",
        ),
        (
            ScamCategory.PONZI_MLM,
            "Guaranteed 10% daily returns! Referral bonus on every downline member.",
        ),
        (
            ScamCategory.BETTING_GAMBLING,
            "Get your betting ID now! 100% sure shot tips, instant withdrawal.",
        ),
        (
            ScamCategory.UTILITY_BILL_SCAM,
            "Your electricity will be disconnected tonight. Update meter immediately.",
        ),
        (
            ScamCategory.OTP_THEFT,
            "This is SBI security. Please share the OTP sent to your registered mobile immediately.",
        ),
        (
            ScamCategory.KYC_SCAM,
            "Dear customer your SBI KYC will be blocked in 24 hours. Verify immediately.",
        ),
        (
            ScamCategory.UPI_FRAUD,
            "Approve this UPI collect request to receive your refund of Rs 5000.",
        ),
        (
            ScamCategory.TECH_SUPPORT,
            "Install AnyDesk so our executive can fix your bank account problem remotely.",
        ),
    ],
)
def test_each_fraud_family_is_classified_correctly(
    analyzer: RuleBasedFallbackAnalyzer, expected: ScamCategory, message: str
) -> None:
    assert analyzer.analyze(message).scam_category is expected


def test_courier_scam_is_not_romance(analyzer: RuleBasedFallbackAnalyzer) -> None:
    """'parcel' plus 'customs' alone is a courier scam, not romance fraud."""

    result = analyzer.analyze(
        "Your parcel is held at customs, pay the fee to release the package."
    )
    assert result.scam_category is not ScamCategory.ROMANCE_SCAM


def test_advance_fee_does_not_override_the_fraud_family(
    analyzer: RuleBasedFallbackAnalyzer,
) -> None:
    """A registration fee is a tactic; it must not claim the category."""

    result = analyzer.analyze(
        "Data entry work from home, earn 1200 per hour. Registration fee 499 applies."
    )
    assert result.scam_category is ScamCategory.FAKE_JOB


def test_advance_fee_alone_still_raises_risk(analyzer: RuleBasedFallbackAnalyzer) -> None:
    """Carrying no category must not mean carrying no weight."""

    result = analyzer.analyze("Pay an advance fee of Rs 2000 to proceed with your request.")
    assert result.verdict in {Verdict.SUSPICIOUS, Verdict.SCAM}


def test_genuine_message_is_not_flagged(analyzer: RuleBasedFallbackAnalyzer) -> None:
    result = analyzer.analyze(
        "Your order 4471239 has been dispatched and will arrive on Tuesday "
        "between 10am and 2pm. No action is needed."
    )
    assert result.verdict is Verdict.SAFE
