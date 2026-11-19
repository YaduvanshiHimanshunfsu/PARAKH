from __future__ import annotations

import pytest

from app.schemas import IdentifierType
from app.services.identifier_extractor import extract_identifiers, merge_identifiers


def values_of(text: str, kind: IdentifierType) -> set[str]:
    return {item.value for item in extract_identifiers(text) if item.type is kind}


# --- phones ---------------------------------------------------------------

@pytest.mark.parametrize(
    "text",
    [
        "Call 9876543210 now",
        "Call 9876543210. Then stop.",          # sentence-ending period
        "Contact +91 98765 43210 today",
        "Reach +919876543210",
        "WhatsApp 98765-43210",
    ],
)
def test_indian_mobiles_normalise_to_one_value(text: str) -> None:
    assert values_of(text, IdentifierType.PHONE) == {"+919876543210"}


@pytest.mark.parametrize(
    "text",
    [
        "Aadhaar 987654321012 linked",   # 12 digits, not a mobile
        "Landline 0112345678 only",      # does not start 6-9 after trunk strip
        "Version 1.2.3.4 released",
        "Order 12345678901 shipped",     # 11 digits starting with 1
    ],
)
def test_non_mobile_digit_runs_are_not_phones(text: str) -> None:
    assert values_of(text, IdentifierType.PHONE) == set()


def test_transaction_context_lowers_phone_confidence() -> None:
    plain = extract_identifiers("Call 9876543210")[0]
    noisy = [i for i in extract_identifiers("Order ref 9876543210") if i.type is IdentifierType.PHONE][0]
    assert noisy.confidence < plain.confidence


# --- UPI vs email ---------------------------------------------------------

def test_upi_handle_without_dot_is_upi() -> None:
    assert values_of("Pay to rajesh@okaxis now", IdentifierType.UPI) == {"rajesh@okaxis"}


def test_email_is_not_misread_as_upi() -> None:
    text = "Mail support@hdfcbank.com for help"
    assert values_of(text, IdentifierType.EMAIL) == {"support@hdfcbank.com"}
    assert values_of(text, IdentifierType.UPI) == set()


def test_known_psp_handle_scores_higher_than_unknown() -> None:
    known = [i for i in extract_identifiers("pay rajesh@okaxis") if i.type is IdentifierType.UPI][0]
    unknown = [i for i in extract_identifiers("pay rajesh@zzqqhandle") if i.type is IdentifierType.UPI][0]
    assert known.confidence > unknown.confidence


def test_email_and_upi_coexist_in_one_message() -> None:
    text = "Mail support@hdfcbank.com or pay shop@paytm"
    assert values_of(text, IdentifierType.EMAIL) == {"support@hdfcbank.com"}
    assert values_of(text, IdentifierType.UPI) == {"shop@paytm"}


# --- banking --------------------------------------------------------------

def test_bank_account_requires_banking_context() -> None:
    assert values_of("Deposit to A/c 123456789012 today", IdentifierType.BANK_ACCOUNT) == {"123456789012"}
    assert values_of("Reference 123456789012 logged", IdentifierType.BANK_ACCOUNT) == set()


def test_ifsc_requires_zero_in_fifth_position() -> None:
    assert values_of("IFSC HDFC0001234", IdentifierType.IFSC) == {"HDFC0001234"}
    assert values_of("Code HDFC1001234", IdentifierType.IFSC) == set()


# --- crypto ---------------------------------------------------------------

def test_eth_address_is_lowercased() -> None:
    text = "Send to 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb1"
    assert values_of(text, IdentifierType.CRYPTO_ETH) == {"0x742d35cc6634c0532925a3b844bc9e7595f0beb1"}


def test_btc_address_preserves_case() -> None:
    text = "BTC 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
    assert values_of(text, IdentifierType.CRYPTO_BTC) == {"1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"}


# --- urls, domains, IPs ---------------------------------------------------

def test_url_also_yields_its_registered_host_as_domain() -> None:
    found = extract_identifiers("Visit https://sbi-verify-kyc.in/urgent now")
    assert any(i.type is IdentifierType.URL for i in found)
    assert "sbi-verify-kyc.in" in values_of("Visit https://sbi-verify-kyc.in/urgent now", IdentifierType.DOMAIN)


def test_ip_hosted_url_yields_ip_not_domain() -> None:
    text = "Beacon to http://45.133.1.9/api"
    assert values_of(text, IdentifierType.IP) == {"45.133.1.9"}
    assert values_of(text, IdentifierType.DOMAIN) == set()


def test_private_and_loopback_addresses_are_ignored() -> None:
    text = "Internal 192.168.1.1 and 127.0.0.1 and 10.0.0.5"
    assert values_of(text, IdentifierType.IP) == set()


def test_version_string_is_not_an_ip() -> None:
    assert values_of("Build version 8.8.8.8 shipped", IdentifierType.IP) == set()


# --- packages -------------------------------------------------------------

def test_android_package_detected_by_leading_segment() -> None:
    assert values_of("Install com.quickloan.instant today", IdentifierType.PACKAGE) == {"com.quickloan.instant"}


def test_hostname_is_not_misread_as_package() -> None:
    assert values_of("Open mail.google.com for details", IdentifierType.PACKAGE) == set()


# --- telegram -------------------------------------------------------------

def test_telegram_link_is_normalised_without_scheme() -> None:
    assert values_of("Join https://t.me/RichPlan2026 now", IdentifierType.TELEGRAM) == {"t.me/richplan2026"}


# --- general behaviour ----------------------------------------------------

def test_empty_input_returns_nothing() -> None:
    assert extract_identifiers("") == []
    assert extract_identifiers("   ") == []


def test_duplicates_are_collapsed() -> None:
    found = extract_identifiers("Call 9876543210 or 98765 43210 again")
    phones = [i for i in found if i.type is IdentifierType.PHONE]
    assert len(phones) == 1


def test_context_snippet_is_captured() -> None:
    item = extract_identifiers("Please pay rajesh@okaxis immediately")[0]
    assert item.context and "pay" in item.context


def test_context_can_be_disabled() -> None:
    item = extract_identifiers("pay rajesh@okaxis", include_context=False)[0]
    assert item.context is None


def test_merge_keeps_highest_confidence_per_identifier() -> None:
    low = extract_identifiers("Order ref 9876543210")
    high = extract_identifiers("Call 9876543210")
    merged = merge_identifiers(low, high)
    phones = [i for i in merged if i.type is IdentifierType.PHONE]
    assert len(phones) == 1
    assert phones[0].confidence == max(
        i.confidence for i in (*low, *high) if i.type is IdentifierType.PHONE
    )


def test_realistic_ponzi_message_yields_the_money_trail() -> None:
    text = (
        "Guaranteed 10% daily returns! Join t.me/RichPlan2026 . "
        "Deposit to A/c 123456789012 IFSC HDFC0001234 or UPI winner@ybl . "
        "Support 9876543210 . Site https://richplan-invest.xyz/join"
    )
    found = {(i.type, i.value) for i in extract_identifiers(text)}
    expected = {
        (IdentifierType.TELEGRAM, "t.me/richplan2026"),
        (IdentifierType.BANK_ACCOUNT, "123456789012"),
        (IdentifierType.IFSC, "HDFC0001234"),
        (IdentifierType.UPI, "winner@ybl"),
        (IdentifierType.PHONE, "+919876543210"),
        (IdentifierType.DOMAIN, "richplan-invest.xyz"),
    }
    assert expected <= found
