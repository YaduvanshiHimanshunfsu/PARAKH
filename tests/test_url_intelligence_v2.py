from __future__ import annotations

"""URL intelligence v2: no official-domain false positives (planversionalpha.md B.4)."""

import asyncio

import pytest

from app.config import Settings
from app.data.protected_brands import PROTECTED_BRANDS, is_official_domain
from app.services.link_service import links_cases
from app.services.url_intelligence import MAX_URLS_PER_MESSAGE, UrlIntelligenceService, host_tokens, static_url_risk
from app.utils.lookalike import lookalike_match, osa_distance, skeleton


@pytest.fixture(scope="module")
def service() -> UrlIntelligenceService:
    return UrlIntelligenceService(
        Settings(gemini_api_key=None, url_tls_probe_enabled=False, domain_age_enabled=False)
    )


def analyse(service: UrlIntelligenceService, url: str):
    return asyncio.run(service.analyze_url(url))


OFFICIAL = [
    "https://police.rajasthan.gov.in",
    "https://rajasthan.gov.in",
    "https://sso.rajasthan.gov.in/signin",
    "https://janaadhaar.rajasthan.gov.in",
    "https://emitra.rajasthan.gov.in",
    "https://energy.rajasthan.gov.in",
    "https://cybercrime.gov.in",
    "https://www.incometax.gov.in",
    "https://uidai.gov.in",
    "https://myaadhaar.uidai.gov.in",
    "https://epfindia.gov.in",
    "https://pmkisan.gov.in",
    "https://digilocker.gov.in",
    "https://sancharsaathi.gov.in",
    "https://parivahan.gov.in",
    "https://echallan.parivahan.gov.in",
    "https://gst.gov.in",
    "https://sebi.gov.in",
    "https://rbi.org.in",
    "https://sbi.co.in",
    "https://onlinesbi.sbi",
    "https://sbicard.com",
    "https://hdfcbank.com",
    "https://icicibank.com",
    "https://axisbank.com",
    "https://pnbindia.in",
    "https://bankofbaroda.in",
    "https://paytm.com",
    "https://phonepe.com",
    "https://npci.org.in",
    "https://jvvnl.in",
    "https://avvnl.com",
    "https://jdvvnl.com",
    "https://airtel.in",
    "https://jio.com",
    "https://indiapost.gov.in",
    "https://irctc.co.in",
    # Ordinary sites that merely contain brand-like substrings (defect D1).
    "https://firstpost.com",
    "https://pineapple.com",
    "https://government-jobs-alert.in",
]


@pytest.mark.parametrize("url", OFFICIAL)
def test_official_and_ordinary_domains_get_no_brand_signal(service, url):
    result = analyse(service, url)
    codes = {signal.code for signal in result.signals}
    assert "BRAND_LIKE_DOMAIN" not in codes, f"{url}: {codes}"
    assert "LOOKALIKE_DOMAIN" not in codes, f"{url}: {codes}"
    assert result.risk_level.value == "LOW", f"{url} -> {result.risk_level.value} {codes}"


LOOKALIKES = [
    ("https://sbi-verify-kyc.in/urgent", "BRAND_LIKE_DOMAIN"),
    ("https://sbi-kyc-help.cyou", "BRAND_LIKE_DOMAIN"),
    ("https://hdfc-kyc-update.xyz/login", "BRAND_LIKE_DOMAIN"),
    ("https://jvvnl-bill-pay.in", "BRAND_LIKE_DOMAIN"),
    ("https://sso-rajasthan-verify.online", "BRAND_LIKE_DOMAIN"),
    ("https://hdfcbnak.com", "LOOKALIKE_DOMAIN"),
    ("https://sbii.co.in", "LOOKALIKE_DOMAIN"),
    ("https://rnicrosoft.com", "LOOKALIKE_DOMAIN"),
    ("https://jvvn1-bill.in", "LOOKALIKE_DOMAIN"),
]


@pytest.mark.parametrize("url,expected", LOOKALIKES, ids=[case[0] for case in LOOKALIKES])
def test_lookalike_domains_are_flagged(service, url, expected):
    result = analyse(service, url)
    codes = {signal.code for signal in result.signals}
    assert expected in codes, f"{url}: {codes}"
    assert result.risk_level.value in {"MEDIUM", "HIGH", "CRITICAL"}


def test_suspicious_tld_list_covers_the_current_abuse_set(service):
    codes = {signal.code for signal in analyse(service, "https://example.cyou").signals}
    assert "HIGH_RISK_TLD" in codes


def test_url_cap_raised_and_extraction_deduplicates():
    message = " ".join(f"http://site{i}.example/path" for i in range(14))
    urls = UrlIntelligenceService.extract_urls(message)
    assert len(urls) == MAX_URLS_PER_MESSAGE
    assert UrlIntelligenceService.extract_urls("a.example and A.EXAMPLE") == ["a.example"]


def test_host_tokens_excludes_the_public_suffix():
    assert host_tokens("sbi-verify-kyc.in", "in") == {"sbi", "verify", "kyc"}
    assert "in" not in host_tokens("secure.sbi-login.co.in", "co.in")


# --- look-alike maths -------------------------------------------------------


def test_osa_distance_counts_transposition_as_one_edit():
    assert osa_distance("hdfcbank", "hdfcbnak") == 1
    assert osa_distance("sbi", "sbi") == 0
    assert osa_distance("abcdef", "uvwxyz", cutoff=2) == 3


def test_skeleton_folds_visual_confusables():
    assert skeleton("rnicrosoft") == skeleton("microsoft")
    assert skeleton("jvvn1") == skeleton("jvvnl")
    assert skeleton("paypa1") == skeleton("paypal")


def test_exact_brand_label_is_not_a_lookalike():
    assert lookalike_match("hdfcbank") is None
    assert lookalike_match("sbi") is None


def test_unrelated_words_are_not_lookalikes():
    for word in ("firstpost", "pineapple", "example", "rajasthantourism", "news"):
        assert lookalike_match(word) is None, word


# --- D6: an impersonated brand's real domain links nothing -----------------


@pytest.mark.parametrize(
    "domain",
    ["sbi.co.in", "incometax.gov.in", "police.rajasthan.gov.in", "uidai.gov.in", "hdfcbank.com"],
)
def test_official_domains_do_not_link_cases(domain):
    assert links_cases("DOMAIN", domain) is False


@pytest.mark.parametrize("domain", ["sbi-verify-kyc.in", "richplan-invest.xyz", "hdfcbnak.com"])
def test_scam_domains_still_link_cases(domain):
    assert links_cases("DOMAIN", domain) is True


def test_protected_brand_domains_are_recognised_as_official():
    for brand in PROTECTED_BRANDS:
        for domain in brand.domains:
            assert is_official_domain(domain), domain


def test_static_url_risk_matches_the_full_analyser(service):
    for url in ("https://sbi-verify-kyc.in/urgent", "https://police.rajasthan.gov.in", "bit.ly/abc"):
        quick = static_url_risk(url)
        full = analyse(service, url)
        assert quick.score == full.risk_score
        assert set(quick.codes) == {signal.code for signal in full.signals}
