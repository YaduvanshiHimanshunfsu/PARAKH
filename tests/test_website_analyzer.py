from __future__ import annotations

"""Website content analysis tests (Phase 4).

Rule scoring is tested against constructed pages so the suite stays offline and
deterministic. Fetch safety is tested separately — those cases are rejected
before any network call is made.
"""

import asyncio

import pytest

from app.config import Settings
from app.schemas import ArtifactType, IdentifierType, RiskLevel, Severity
from app.services.website_analyzer import WebsiteAnalyzer, WebsiteFetchError


@pytest.fixture()
def analyzer() -> WebsiteAnalyzer:
    return Settings() and WebsiteAnalyzer(Settings())


def page_from_html(analyzer: WebsiteAnalyzer, html: str, url: str = "https://scam.test/join"):
    """Build a FetchedPage from markup without touching the network."""

    return analyzer._build_page(url, url, 200, "text/html", html.encode("utf-8"), [url], False)


PONZI_HTML = """
<html><head><title>RichPlan Investment</title></head><body>
  <h1>Guaranteed returns on every deposit</h1>
  <p>Earn 10% daily on your investment. 100% safe, zero risk.</p>
  <p>Referral bonus on every downline member you add. Binary plan available.</p>
  <p>Joining package starts at Rs 5000. Activate your ID today!</p>
  <p>Pay via UPI winner@ybl or deposit to A/c 123456789012 IFSC HDFC0001234</p>
  <p>Contact 9876543210. <a href="https://t.me/RichPlan2026">Join our Telegram</a></p>
  <p>Limited slots left, hurry!</p>
</body></html>
"""

BETTING_HTML = """
<html><head><title>Lucky Bet Pro</title></head><body>
  <h1>Get your betting ID now</h1>
  <p>Colour prediction and aviator game available. 100% winning tips.</p>
  <p>Welcome bonus on first deposit. Instant withdrawal guaranteed.</p>
  <p>Deposit via UPI luckybet@paytm</p>
</body></html>
"""

LOAN_HTML = """
<html><head><title>QuickCash Loan</title></head><body>
  <h1>Instant loan in 5 minutes</h1>
  <p>No CIBIL check, no documents, only Aadhaar needed.</p>
  <p><a href="https://quickcash.test/app.apk">Download our APK</a></p>
  <p>Pay processing fee to quickcash@okaxis</p>
</body></html>
"""

LEGITIMATE_HTML = """
<html><head><title>Anand Stationery Supplies</title></head><body>
  <h1>Office stationery since 1994</h1>
  <p>We supply notebooks, pens and printer paper to offices across Jaipur.</p>
  <p>Registered office: 14 MI Road, Jaipur. CIN U12345RJ1994PTC001234</p>
  <a href="/privacy-policy">Privacy Policy</a>
  <a href="/terms-and-conditions">Terms and Conditions</a>
  <a href="/contact-us">Contact Us</a>
  <a href="/refund-policy">Refund Policy</a>
</body></html>
"""


# --- parsing --------------------------------------------------------------


def test_title_and_visible_text_are_extracted(analyzer: WebsiteAnalyzer) -> None:
    page = page_from_html(analyzer, PONZI_HTML)
    assert page.title == "RichPlan Investment"
    assert "Guaranteed returns" in page.text


def test_scripts_and_styles_are_stripped(analyzer: WebsiteAnalyzer) -> None:
    html = "<html><body><script>var secret='hidden';</script><style>p{color:red}</style><p>Visible</p></body></html>"
    page = page_from_html(analyzer, html)
    assert "Visible" in page.text
    assert "secret" not in page.text
    assert "color:red" not in page.text


def test_links_and_form_fields_are_captured(analyzer: WebsiteAnalyzer) -> None:
    html = '<html><body><a href="https://x.test/a">go</a><form><input name="upi_id"></form></body></html>'
    page = page_from_html(analyzer, html)
    assert "https://x.test/a" in page.links
    assert "upi_id" in page.form_fields


def test_malformed_html_does_not_raise(analyzer: WebsiteAnalyzer) -> None:
    page = page_from_html(analyzer, "<html><body><p>unclosed <div>tags")
    assert "unclosed" in page.text


# --- Ponzi / MLM ----------------------------------------------------------


def test_ponzi_site_scores_high(analyzer: WebsiteAnalyzer) -> None:
    bundle = analyzer.analyze_page(page_from_html(analyzer, PONZI_HTML))
    assert bundle.risk_level is RiskLevel.HIGH
    assert bundle.risk_score >= 70


@pytest.mark.parametrize(
    "code",
    [
        "GUARANTEED_RETURNS",
        "DAILY_RETURN_PERCENTAGE",
        "NO_RISK_CLAIM",
        "REFERRAL_CHAIN_INCOME",
        "JOINING_PACKAGE_FEE",
    ],
)
def test_ponzi_indicators_are_individually_reported(analyzer: WebsiteAnalyzer, code: str) -> None:
    """PS01 wants the specific indicators that triggered the result."""

    codes = {f.code for f in analyzer.analyze_page(page_from_html(analyzer, PONZI_HTML)).findings}
    assert code in codes


def test_every_finding_cites_evidence_from_the_page(analyzer: WebsiteAnalyzer) -> None:
    bundle = analyzer.analyze_page(page_from_html(analyzer, PONZI_HTML))
    rule_findings = [f for f in bundle.findings if f.code.isupper() and f.evidence]
    assert rule_findings
    for finding in rule_findings:
        assert len(finding.explanation) > 20


# --- betting --------------------------------------------------------------


def test_betting_site_is_detected(analyzer: WebsiteAnalyzer) -> None:
    bundle = analyzer.analyze_page(page_from_html(analyzer, BETTING_HTML))
    codes = {f.code for f in bundle.findings}
    assert "BETTING_PLATFORM" in codes
    assert "PREDICTION_GAME" in codes
    assert bundle.risk_level is RiskLevel.HIGH


def test_sure_winning_tips_flagged(analyzer: WebsiteAnalyzer) -> None:
    codes = {f.code for f in analyzer.analyze_page(page_from_html(analyzer, BETTING_HTML)).findings}
    assert "SURE_WINNING_TIPS" in codes


# --- predatory lending ----------------------------------------------------


def test_loan_site_with_direct_apk_is_flagged(analyzer: WebsiteAnalyzer) -> None:
    codes = {f.code for f in analyzer.analyze_page(page_from_html(analyzer, LOAN_HTML)).findings}
    assert "INSTANT_LOAN_NO_CHECKS" in codes
    assert "DIRECT_APK_DOWNLOAD" in codes


# --- identifier harvesting (the money trail) ------------------------------


def test_payment_identifiers_are_harvested_from_page_content(analyzer: WebsiteAnalyzer) -> None:
    bundle = analyzer.analyze_page(page_from_html(analyzer, PONZI_HTML))
    found = {(i.type, i.value) for i in bundle.identifiers}
    assert (IdentifierType.UPI, "winner@ybl") in found
    assert (IdentifierType.IFSC, "HDFC0001234") in found
    assert (IdentifierType.BANK_ACCOUNT, "123456789012") in found
    assert (IdentifierType.PHONE, "+919876543210") in found


def test_payment_identifiers_raise_a_finding(analyzer: WebsiteAnalyzer) -> None:
    codes = {f.code for f in analyzer.analyze_page(page_from_html(analyzer, PONZI_HTML)).findings}
    assert "PAGE_COLLECTS_PAYMENT_IDENTIFIER" in codes


def test_telegram_funnel_is_detected_from_a_link(analyzer: WebsiteAnalyzer) -> None:
    bundle = analyzer.analyze_page(page_from_html(analyzer, PONZI_HTML))
    telegram = {i.value for i in bundle.identifiers if i.type is IdentifierType.TELEGRAM}
    assert "t.me/richplan2026" in telegram


def test_upi_deep_link_is_extracted(analyzer: WebsiteAnalyzer) -> None:
    html = '<html><body><a href="upi://pay?pa=scammer@okaxis&am=500">Pay now</a></body></html>'
    bundle = analyzer.analyze_page(page_from_html(analyzer, html))
    upi = {i.value for i in bundle.identifiers if i.type is IdentifierType.UPI}
    assert "scammer@okaxis" in upi


# --- legitimacy markers ---------------------------------------------------


def test_money_site_missing_disclosures_is_flagged(analyzer: WebsiteAnalyzer) -> None:
    html = "<html><body><p>Deposit now and invest with us! Pay via UPI.</p></body></html>"
    codes = {f.code for f in analyzer.analyze_page(page_from_html(analyzer, html)).findings}
    assert "MISSING_LEGITIMACY_MARKERS" in codes


def test_site_with_full_disclosures_is_not_flagged(analyzer: WebsiteAnalyzer) -> None:
    codes = {f.code for f in analyzer.analyze_page(page_from_html(analyzer, LEGITIMATE_HTML)).findings}
    assert "MISSING_LEGITIMACY_MARKERS" not in codes


def test_legitimate_business_site_is_low_risk(analyzer: WebsiteAnalyzer) -> None:
    """A real business page must not be swept up by the fraud rules."""

    bundle = analyzer.analyze_page(page_from_html(analyzer, LEGITIMATE_HTML))
    assert bundle.risk_level is RiskLevel.LOW


# --- bundle contract and limitations --------------------------------------


def test_bundle_matches_the_shared_contract(analyzer: WebsiteAnalyzer) -> None:
    bundle = analyzer.analyze_page(page_from_html(analyzer, PONZI_HTML))
    assert bundle.artifact_type is ArtifactType.WEBSITE
    assert 0 <= bundle.risk_score <= 100
    assert bundle.content_sha256 and len(bundle.content_sha256) == 64
    assert bundle.simhash
    assert bundle.details["title"] == "RichPlan Investment"


def test_snapshot_preserves_evidence(analyzer: WebsiteAnalyzer) -> None:
    text = analyzer.analyze_page(page_from_html(analyzer, PONZI_HTML)).content_text or ""
    assert "URL:" in text and "Guaranteed returns" in text


def test_thin_content_is_reported_as_a_limitation(analyzer: WebsiteAnalyzer) -> None:
    """A JS-rendered page must not look clean just because no text came back."""

    bundle = analyzer.analyze_page(page_from_html(analyzer, "<html><body></body></html>"))
    limitations = " ".join(bundle.details["limitations"])
    assert "JavaScript" in limitations


def test_limitations_always_state_no_js_execution(analyzer: WebsiteAnalyzer) -> None:
    bundle = analyzer.analyze_page(page_from_html(analyzer, LEGITIMATE_HTML))
    assert any("No JavaScript was executed" in item for item in bundle.details["limitations"])


def test_analysis_is_deterministic(analyzer: WebsiteAnalyzer) -> None:
    first = analyzer.analyze_page(page_from_html(analyzer, PONZI_HTML))
    second = analyzer.analyze_page(page_from_html(analyzer, PONZI_HTML))
    assert first.risk_score == second.risk_score


# --- fetch safety ---------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/admin",
        "http://169.254.169.254/latest/meta-data/",
        "http://192.168.0.1/",
        "file:///etc/passwd",
    ],
)
def test_fetch_refuses_unsafe_targets(analyzer: WebsiteAnalyzer, url: str) -> None:
    """The guard must reject before any request is made."""

    with pytest.raises(WebsiteFetchError):
        asyncio.run(analyzer.fetch(url))
