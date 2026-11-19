from __future__ import annotations

"""Content fingerprinting tests.

Phase 5 campaign detection is built on these two functions, so their behaviour
is pinned here before anything depends on it.
"""

import pytest

from app.utils.fingerprint import (
    NEAR_DUPLICATE_THRESHOLD,
    NUM_TOKEN,
    URL_TOKEN,
    content_hash,
    hamming_distance,
    is_near_duplicate,
    normalise_for_hashing,
    simhash,
)

TEMPLATE_A = "Your KYC will be blocked in 24 hours. Pay 500 at http://pay-now.in/a"
TEMPLATE_B = "Your KYC will be blocked in 48 hours. Pay 900 at http://other-site.in/b"
UNRELATED = "Congratulations, you have won a lottery prize of 45 lakh rupees today"


# --- normalisation --------------------------------------------------------

def test_digits_and_urls_are_masked() -> None:
    normalised = normalise_for_hashing(TEMPLATE_A)
    assert NUM_TOKEN in normalised
    assert URL_TOKEN in normalised
    assert "500" not in normalised
    assert "pay-now.in" not in normalised


def test_normalisation_is_case_insensitive() -> None:
    assert normalise_for_hashing("PAY NOW") == normalise_for_hashing("pay now")


# --- exact template matching ----------------------------------------------

def test_same_template_with_different_values_shares_a_hash() -> None:
    """The core campaign-detection requirement: one template, many sends."""

    assert content_hash(TEMPLATE_A) == content_hash(TEMPLATE_B)


def test_different_messages_do_not_share_a_hash() -> None:
    assert content_hash(TEMPLATE_A) != content_hash(UNRELATED)


def test_hash_is_stable_across_calls() -> None:
    assert content_hash(TEMPLATE_A) == content_hash(TEMPLATE_A)


# --- simhash --------------------------------------------------------------

def test_simhash_is_sixteen_hex_characters() -> None:
    value = simhash(TEMPLATE_A)
    assert len(value) == 16
    int(value, 16)  # must parse as hex


def test_reworded_variant_is_a_near_duplicate() -> None:
    original = "Dear customer your account will be blocked today, verify your KYC immediately"
    reworded = "Dear customer your account will be blocked today, verify your KYC right now"
    assert is_near_duplicate(simhash(original), simhash(reworded))


def test_unrelated_messages_are_far_apart() -> None:
    assert hamming_distance(simhash(TEMPLATE_A), simhash(UNRELATED)) > NEAR_DUPLICATE_THRESHOLD


BASE = "Dear customer your bank account will be suspended today, verify your KYC immediately now"


@pytest.mark.parametrize(
    "variant",
    [
        "Dear customer your bank account will be suspended today, verify your KYC right away now",
        "Dear customer your bank account will be frozen today, confirm your KYC right away now",
        "Dear customer your bank account will be suspended today, immediately verify your KYC now",
    ],
)
def test_reworded_campaign_variants_stay_inside_the_threshold(variant: str) -> None:
    """Character n-grams, not word shingles.

    With word 5-grams a two-word edit measured 34 bits — indistinguishable from
    unrelated text at 35. These cases pin the separation that fix restored.
    """

    assert hamming_distance(simhash(BASE), simhash(variant)) <= NEAR_DUPLICATE_THRESHOLD


@pytest.mark.parametrize(
    "unrelated",
    [
        "Your Amazon order 11223344 has shipped and arrives Tuesday",
        "Congratulations you won a lottery prize of 45 lakh rupees today",
        "Work from home and earn 1500 per hour liking YouTube videos daily",
        "Just checking in about the meeting tomorrow afternoon at the office",
    ],
)
def test_unrelated_messages_stay_outside_the_threshold(unrelated: str) -> None:
    assert hamming_distance(simhash(BASE), simhash(unrelated)) > NEAR_DUPLICATE_THRESHOLD


def test_identical_text_has_zero_distance() -> None:
    assert hamming_distance(simhash(TEMPLATE_A), simhash(TEMPLATE_A)) == 0


# --- edge cases -----------------------------------------------------------

def test_empty_text_does_not_raise() -> None:
    assert simhash("") == "0" * 16
    assert len(content_hash("")) == 64


def test_short_text_still_produces_a_fingerprint() -> None:
    assert simhash("hi") != ""


def test_malformed_simhash_comparison_returns_max_distance() -> None:
    assert hamming_distance("not-hex", "also-not-hex") == 64
