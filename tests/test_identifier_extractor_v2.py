from __future__ import annotations

"""Identifier extractor v2 and identifier roles (planversionalpha.md B.5, B.6)."""

import pytest

from app.schemas import Identifier, IdentifierType
from app.services.identifier_extractor import extract_identifiers
from app.services.identifier_roles import IdentifierRole, classify, links_cases_with_role
from app.utils.checksums import (
    is_base58_bitcoin_address,
    is_bech32_bitcoin_address,
    is_tron_address,
    luhn_ok,
)


def pairs(text: str) -> set[tuple[str, str]]:
    return {(item.type.value, item.value) for item in extract_identifiers(text, include_context=False)}


# --- new types --------------------------------------------------------------


def test_telegram_bot_token_is_not_read_as_a_phone_number():
    """Defect D5: 7012345678:AAH... used to be reported as +917012345678."""

    found = pairs("bot token 7012345678:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw0")
    assert ("TELEGRAM_BOT", "7012345678") in found
    assert not any(kind == "PHONE" for kind, _ in found)


def test_bot_token_inside_a_telegram_api_url():
    found = pairs("https://api.telegram.org/bot6543210987:AAFkLmNoPqRsTuVwXyZaBcDeFgHiJkLmNoP/sendMessage")
    assert ("TELEGRAM_BOT", "6543210987") in found


def test_bot_token_is_stored_masked():
    """PARAKH records the token as evidence but must never be able to use it."""

    [found] = [i for i in extract_identifiers("token 7012345678:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw0")
               if i.type is IdentifierType.TELEGRAM_BOT]
    assert found.value == "7012345678"
    assert "AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw0" not in found.raw_value
    assert found.raw_value.startswith("7012345678:AAHd")


def test_tron_address_requires_a_valid_checksum():
    assert ("CRYPTO_TRON", "TKArzRcd5hxJZZ6QtCppxs3D3M7UqPTq65") in pairs(
        "Send USDT TRC20 to TKArzRcd5hxJZZ6QtCppxs3D3M7UqPTq65"
    )
    # Same shape, broken checksum.
    assert not any(kind == "CRYPTO_TRON" for kind, _ in pairs("Send to TKArzRcd5hxJZZ6QtCppxs3D3M7UqPTq66"))


def test_bitcoin_address_requires_a_valid_checksum():
    assert ("CRYPTO_BTC", "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa") in pairs(
        "Pay 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
    )
    assert not any(kind == "CRYPTO_BTC" for kind, _ in pairs("Pay 1A1zP1eP5QGefi2DMPTfTL5SLmv7Divfaa"))


def test_imei_needs_luhn_and_a_keyword():
    assert ("IMEI", "490154203237518") in pairs("Handset IMEI 490154203237518 was used")
    # Valid Luhn, but no IMEI keyword: could be any reference number.
    assert not any(kind == "IMEI" for kind, _ in pairs("Reference 490154203237518 recorded"))
    # IMEI keyword, invalid Luhn.
    assert not any(kind == "IMEI" for kind, _ in pairs("IMEI 123456789012345 noted"))


def test_firebase_endpoint_is_reported_alongside_the_url():
    found = pairs("Data sent to https://quickcash-abc.firebaseio.com/users.json")
    assert ("FIREBASE_DB", "quickcash-abc.firebaseio.com") in found
    assert ("DOMAIN", "quickcash-abc.firebaseio.com") in found
    assert any(kind == "URL" for kind, _ in found)


# --- rewritten types --------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("WhatsApp our agent on +92 300 1234567 for the bonus.", "+923001234567"),
        ("Call +1 415 555 0132 now", "+14155550132"),
        ("Dubai office +971 50 123 4567", "+971501234567"),
        ("Office landline 0141-2741234, Jaipur.", "+911412741234"),
        ("Contact 098123-45670 today", "+919812345670"),
    ],
)
def test_phone_numbers_beyond_indian_mobiles(text, expected):
    assert ("PHONE", expected) in pairs(text)


def test_order_numbers_are_not_phone_numbers():
    assert not any(kind == "PHONE" for kind, _ in pairs("Your order 4471239 has been dispatched"))


def test_upi_id_built_from_a_mobile_number_is_not_split():
    found = pairs("Send to 9812345670@ybl today")
    assert ("UPI", "9812345670@ybl") in found
    assert not any(kind == "PHONE" for kind, _ in found)


@pytest.mark.parametrize(
    "host",
    ["sbi-kyc-help.cyou", "task-earn.sbs", "quick-loan.bond", "bet-now.icu", "bit.ly"],
)
def test_new_tlds_are_recognised_through_the_public_suffix_list(host):
    assert ("DOMAIN", host) in pairs(f"Go to {host}/now today")


def test_non_hosts_are_not_domains():
    for text in ("See report.pdf attached", "call sendMessage() next"):
        assert not any(kind == "DOMAIN" for kind, _ in pairs(text))


def test_bare_telegram_handle_needs_telegram_context():
    assert ("TELEGRAM", "t.me/richplansupport") in pairs("Join our Telegram @RichPlanSupport for profit")
    assert not any(kind == "TELEGRAM" for kind, _ in pairs("Thanks @RichPlanSupport for the update"))


# --- checksums --------------------------------------------------------------


def test_checksum_helpers():
    assert is_tron_address("TAzXbaDyfDaC66AsmF3QYs11NpRyot9uR9")
    assert not is_tron_address("TAzXbaDyfDaC66AsmF3QYs11NpRyot9uR0")
    assert is_base58_bitcoin_address("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
    assert is_bech32_bitcoin_address("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4")
    assert not is_bech32_bitcoin_address("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t5")
    assert luhn_ok("490154203237518")
    assert not luhn_ok("490154203237519")


# --- B.6 roles --------------------------------------------------------------


def identifier(kind: IdentifierType, value: str, context: str = "") -> Identifier:
    return Identifier(type=kind, value=value, raw_value=value, context=context or None, confidence=90)


def test_official_helpline_is_not_a_suspect():
    role = classify(identifier(IdentifierType.PHONE, "+911930", "call 1930 to report"))
    assert role is IdentifierRole.OFFICIAL_CONTACT
    assert links_cases_with_role(role.value) is False


def test_impersonated_brand_domain_does_not_link_cases():
    role = classify(identifier(IdentifierType.DOMAIN, "sbi.co.in", "visit sbi.co.in for details"))
    assert role is IdentifierRole.IMPERSONATED_BRAND
    assert links_cases_with_role(role.value) is False


def test_payment_instruction_marks_a_suspect():
    role = classify(identifier(IdentifierType.UPI, "richplan@ybl", "Pay Rs 5000 to richplan@ybl now"))
    assert role is IdentifierRole.SUSPECT
    assert links_cases_with_role(role.value) is True


def test_reporter_note_marks_the_victims_own_number():
    victim = identifier(IdentifierType.PHONE, "+919876543210", "9876543210")
    role = classify(victim, reporter_note="My number is 9876543210 and I lost money to 9812345670")
    assert role is IdentifierRole.VICTIM
    assert links_cases_with_role(role.value) is False


def test_unknown_role_still_links():
    role = classify(identifier(IdentifierType.UPI, "someone@okaxis", "seen in the chat"))
    assert role is IdentifierRole.UNKNOWN
    assert links_cases_with_role(role.value) is True


def test_officer_choice_overrides_the_automatic_role():
    role = classify(
        identifier(IdentifierType.UPI, "richplan@ybl", "Pay Rs 5000 to richplan@ybl"),
        officer_role="VICTIM",
    )
    assert role is IdentifierRole.VICTIM
