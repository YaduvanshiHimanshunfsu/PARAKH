from __future__ import annotations

import re

from app.utils.text_normalise import find, normalise


def test_dotted_and_dashed_acronyms_collapse():
    assert "KYC" in normalise("Update your K.Y.C today").text
    assert "OTP" in normalise("share O-T-P now").text
    assert "UPI" in normalise("U P I collect").text


def test_ordinary_initials_are_not_collapsed():
    # "A.B.C" is not a known acronym, so it is left alone.
    assert normalise("Mr. A.B.C Sharma").text == "Mr. A.B.C Sharma"


def test_cyrillic_lookalikes_fold_to_latin():
    disguised = "Your КYС is pending"  # К Y С (Cyrillic K and S)
    assert "KYC" in normalise(disguised).text


def test_real_cyrillic_prose_is_not_rewritten():
    text = "Привет, как дела"
    assert normalise(text).text == text


def test_zero_width_characters_are_removed():
    assert normalise("O​T‍P and bl﻿ocked").text == "OTP and blocked"


def test_full_width_characters_fold():
    assert normalise("ＫＹＣ ｕｐｄａｔｅ").text == "KYC update"


def test_leet_tokens_fold_only_when_they_become_keywords():
    view = normalise("Share 0TP and your p1n. Call 9876543210, order 4B12")
    assert "OTP" in view.text
    assert "pin" in view.text
    assert "9876543210" in view.text
    assert "4B12" in view.text


def test_matches_map_back_to_exact_original_text():
    original = "Your K.Y.C will be bl​ocked"
    view = normalise(original)
    phrase, start, end = find(re.compile(r"kyc", re.I), view)
    assert phrase == "K.Y.C"
    assert original[start:end] == "K.Y.C"
    phrase, _, _ = find(re.compile(r"blocked", re.I), view)
    assert phrase == "bl​ocked"


def test_devanagari_round_trip_is_identity():
    original = "आपका खाता बंद कर दिया जाएगा, केवाईसी अपडेट करें"
    view = normalise(original)
    assert view.text == original
    phrase, start, end = find(re.compile("खाता\\s*बंद"), view)
    assert phrase == "खाता बंद" == original[start:end]


def test_empty_text():
    view = normalise("")
    assert view.text == ""
    assert find(re.compile("x"), view) is None
