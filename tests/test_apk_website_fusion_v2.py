from __future__ import annotations

"""APK v2, website v2 and AI fusion (planversionalpha.md B.7, B.8, B.9)."""

import pytest

from app.config import Settings
from app.schemas import AnalysisSource, MediaKind, Verdict
from app.services.apk_analyzer import ApkAnalyzer
from app.services.apk_parsing import decode_base64_strings, detect_packers, dex_strings, inspect_apk
from app.services.fallback_analyzer import RuleBasedFallbackAnalyzer
from app.services.scam_analyzer import ScamAnalyzer
from app.services.website_analyzer import WebsiteAnalyzer, user_agent_for
from tests.apk_fixtures import build_apk

ACCESSIBILITY = "android.permission.BIND_ACCESSIBILITY_SERVICE"
NOTIFICATIONS = "android.permission.BIND_NOTIFICATION_LISTENER_SERVICE"
DEVICE_ADMIN = "android.permission.BIND_DEVICE_ADMIN"
SMS_RECEIVED = "android.provider.Telephony.SMS_RECEIVED"


def codes(bundle) -> set[str]:
    return {finding.code for finding in bundle.findings}


# --- B.7 APK ---------------------------------------------------------------


def test_accessibility_service_declared_on_a_component_is_detected():
    """Defect D8: real malware binds the service, it does not request a permission."""

    data = build_apk("com.fake.bank", bind_services=(("AccessService", ACCESSIBILITY),))
    bundle = ApkAnalyzer().analyze(data, filename="fake.apk")
    assert "ACCESSIBILITY_SERVICE_DECLARED" in codes(bundle)


def test_uses_permission_alone_is_not_the_strong_signal():
    """A uses-permission entry is a request, not a bound service."""

    data = build_apk("com.fake.bank", permissions=(ACCESSIBILITY,))
    facts = inspect_apk(data)
    assert not facts.declared.get("accessibility_service")


def test_notification_listener_and_device_admin_are_detected():
    data = build_apk(
        "com.fake.bank",
        bind_services=(("Notif", NOTIFICATIONS), ("Admin", DEVICE_ADMIN)),
    )
    found = codes(ApkAnalyzer().analyze(data, filename="x.apk"))
    assert "NOTIFICATION_LISTENER_DECLARED" in found
    assert "DEVICE_ADMIN_DECLARED" in found


def test_high_priority_sms_receiver_is_an_interceptor():
    data = build_apk("com.fake.bank", receiver_actions=((SMS_RECEIVED, 999),))
    assert "SMS_INTERCEPT_RECEIVER" in codes(ApkAnalyzer().analyze(data, filename="x.apk"))


def test_ordinary_sms_receiver_is_only_medium():
    data = build_apk("com.fake.bank", receiver_actions=((SMS_RECEIVED, None),))
    found = codes(ApkAnalyzer().analyze(data, filename="x.apk"))
    assert "SMS_RECEIVER_DECLARED" in found
    assert "SMS_INTERCEPT_RECEIVER" not in found


def test_accessibility_plus_sms_is_the_banking_trojan_signature():
    data = build_apk(
        "com.rto.challan",
        bind_services=(("AccessService", ACCESSIBILITY),),
        receiver_actions=((SMS_RECEIVED, 999),),
    )
    bundle = ApkAnalyzer().analyze(data, filename="RTO_Challan.apk")
    assert "BANKING_TROJAN_SIGNATURE" in codes(bundle)
    assert bundle.risk_level.value == "HIGH"


def test_packer_is_named_and_recorded_as_a_limitation():
    data = build_apk("com.packed.app", extra_files=(("lib/arm64-v8a/libjiagu.so", b"\x7fELF" + b"\x00" * 64),))
    facts = inspect_apk(data)
    assert facts.packers == ["Qihoo 360 Jiagu"]
    assert any("packed" in item.lower() for item in facts.limitations)
    assert "PACKED_APP" in codes(ApkAnalyzer().analyze(data, filename="packed.apk"))


def test_clean_app_has_no_packer_or_trojan_signature():
    data = build_apk("com.ordinary.app", permissions=("android.permission.INTERNET",))
    bundle = ApkAnalyzer().analyze(data, filename="ordinary.apk")
    assert detect_packers.__name__  # imported
    assert "BANKING_TROJAN_SIGNATURE" not in codes(bundle)
    assert "PACKED_APP" not in codes(bundle)


def test_bot_token_in_dex_strings_becomes_a_telegram_bot_identifier():
    data = build_apk(
        "com.fake.bank",
        dex_strings=("https://api.telegram.org/bot7012345678:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw0/sendMessage",),
    )
    bundle = ApkAnalyzer().analyze(data, filename="x.apk")
    assert ("TELEGRAM_BOT", "7012345678") in {(i.type.value, i.value) for i in bundle.identifiers}


def test_base64_encoded_endpoint_is_decoded_and_extracted():
    # base64 of https://evil.example/api
    data = build_apk("com.fake.bank", dex_strings=("aHR0cHM6Ly9ldmlsLmV4YW1wbGUvYXBp",))
    bundle = ApkAnalyzer().analyze(data, filename="x.apk")
    assert ("DOMAIN", "evil.example") in {(i.type.value, i.value) for i in bundle.identifiers}


def test_dex_string_table_reader_rejects_non_dex_input():
    assert dex_strings(b"not a dex file") == []


def test_base64_decoder_ignores_binary_and_short_strings():
    assert decode_base64_strings(["short", "////////////////"]) == []


def test_signing_schemes_are_recorded():
    facts = inspect_apk(build_apk("com.example.app"))
    assert isinstance(facts.certificate.schemes, list)


# --- B.8 website -----------------------------------------------------------


def test_fetch_profile_does_not_announce_parakh_by_default():
    """Defect D10: the old agent told the operator an investigator was looking."""

    agent = user_agent_for("mobile")
    assert "PARAKH" not in agent
    assert "Mobile" in agent
    assert "PARAKH" in user_agent_for("transparent")
    assert user_agent_for(None) == user_agent_for("mobile")
    assert user_agent_for("nonsense") == user_agent_for("mobile")


@pytest.fixture()
def website() -> WebsiteAnalyzer:
    return WebsiteAnalyzer(Settings(gemini_api_key=None))


PONZI_HTML = """
<html><head><title>RichPlan Invest - Guaranteed 10% Daily</title>
<script src="/static/kit-main.js"></script><script src="/static/jquery.min.js"></script></head>
<body><h1>Guaranteed returns every day</h1>
<p>Referral bonus on every downline member. Joining package Rs 5000.</p>
<form action="/collect.php"><input name="mobile"><input name="upi_id"><input name="otp"></form>
</body></html>
"""

HINDI_PONZI_HTML = """
<html><head><title>RichPlan</title></head><body>
<h1>गारंटीड रिटर्न रोज़ाना 10%</h1>
<p>रेफरल बोनस पाएं। जॉइनिंग पैकेज 5000 रुपये। निकासी रोक दी गई है, और जमा करें।</p>
</body></html>
"""


def page_for(website: WebsiteAnalyzer, html: str, url: str = "https://richplan-invest.xyz/join"):
    return website._build_page(url, url, 200, "text/html", html.encode("utf-8"), [url], False)


def test_hindi_website_rules_catch_a_hindi_ponzi_page(website):
    bundle = website.analyze_page(page_for(website, HINDI_PONZI_HTML))
    found = codes(bundle)
    assert "GUARANTEED_RETURNS_HI" in found
    assert "REFERRAL_INCOME_HI" in found
    assert bundle.risk_level.value in {"MEDIUM", "HIGH"}


def test_kit_fingerprint_is_stable_and_links_two_deployments(website):
    first = website.analyze_page(page_for(website, PONZI_HTML, "https://richplan-invest.xyz/join"))
    second = website.analyze_page(page_for(website, PONZI_HTML, "https://richplan-pro.top/join"))
    assert first.details["kit_fingerprint"] == second.details["kit_fingerprint"]
    assert set(first.details["kit_fingerprint"]) >= {"form_signature", "script_signature"}

    def kit_values(bundle):
        return {i.value for i in bundle.identifiers if i.raw_value.startswith("kit:")}

    assert kit_values(first) == kit_values(second) != set()


def test_a_different_kit_has_a_different_fingerprint(website):
    other = PONZI_HTML.replace('name="upi_id"', 'name="card_number"').replace("kit-main.js", "other.js")
    first = website.analyze_page(page_for(website, PONZI_HTML))
    second = website.analyze_page(page_for(website, other))
    assert first.details["kit_fingerprint"] != second.details["kit_fingerprint"]


def test_raw_bytes_hash_is_recorded_separately(website):
    bundle = website.analyze_page(page_for(website, PONZI_HTML))
    assert len(bundle.details["raw_sha256"]) == 64
    assert bundle.details["raw_sha256"] != bundle.content_sha256


# --- B.9 AI fusion ---------------------------------------------------------


class _Stub:
    """Minimal stand-in for an AI answer, so no provider call is made."""

    def __init__(self, verdict: Verdict, confidence: int = 90):
        self.verdict = verdict
        self.confidence = confidence


def fuse(message: str, ai_verdict: Verdict):
    from app.schemas import AnalysisResponse

    analyzer = ScamAnalyzer(Settings(gemini_api_key=None))
    ai = AnalysisResponse(
        verdict=ai_verdict,
        confidence=92,
        scam_category="UNKNOWN",
        severity="LOW" if ai_verdict is Verdict.SAFE else "HIGH",
        psychological_tactics=[],
        red_flags=[],
        action_steps=["Verify independently."],
        hindi_summary="जाँच करें।",
        analysis_source=AnalysisSource.AI,
    )
    return analyzer._fuse_with_rules(ai, message, [])


SCAM_TEXT = (
    "This is CBI. A parcel in your name had drugs and a case is registered. You are under "
    "digital arrest, do not disconnect the video call and transfer the bail amount to the "
    "verification account."
)
SAFE_TEXT = "Your order 4471239 has been dispatched and will arrive on Tuesday. No action is needed."


def test_ai_safe_cannot_override_strong_rule_evidence():
    result = fuse(SCAM_TEXT, Verdict.SAFE)
    assert result.verdict is Verdict.SUSPICIOUS
    assert "disagree" in (result.notice or "")
    assert result.safe_explanation is None
    assert result.analysis_source is AnalysisSource.AI_RULES


def test_rule_flags_are_merged_when_both_see_risk():
    result = fuse(SCAM_TEXT, Verdict.SCAM)
    assert result.verdict is Verdict.SCAM
    assert result.red_flags
    for flag in result.red_flags:
        assert flag.phrase in SCAM_TEXT


def test_ai_only_scam_is_labelled_as_such():
    result = fuse(SAFE_TEXT, Verdict.SCAM)
    assert result.verdict is Verdict.SCAM
    assert "offline rules did not find" in (result.notice or "")


def test_fusion_always_attaches_rule_evidence():
    result = fuse(SCAM_TEXT, Verdict.SAFE)
    assert result.rule_evidence
    assert 0.0 <= result.rule_probability <= 1.0
    assert RuleBasedFallbackAnalyzer().analyze(SCAM_TEXT).verdict is Verdict.SCAM
