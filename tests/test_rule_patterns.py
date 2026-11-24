from __future__ import annotations

"""Structural checks on the rule patterns themselves (planversionalpha.md B.3).

The important one is the Devanagari word-boundary trap: Python's ``\\b`` is
defined over ``\\w``, and Devanagari vowel signs (matras) are combining marks
that ``str.isalnum()`` rejects. So ``\\b`` matches *inside* Hindi words, and a
pattern like ``\\bन\\s+करें`` silently matches "स्कैन करें" ("scan it"), turning
an awareness guard into a scam-suppressor. Boundaries next to Devanagari must
use explicit lookarounds instead.
"""

import re

import pytest

from app.data.scam_rules import SCAM_SIGNAL_RULES

DEVANAGARI = re.compile(r"[ऀ-ॿ]")
# \b immediately before or after a Devanagari character in the pattern source.
BAD_BOUNDARY = re.compile(r"(\\b\s*\(?\??:?[^)\]]{0,3}?[ऀ-ॿ])|([ऀ-ॿ][^(\[]{0,3}?\\b)")


def all_patterns():
    for rule in SCAM_SIGNAL_RULES:
        for pattern in rule.patterns:
            yield rule, pattern


def test_no_word_boundary_next_to_devanagari():
    offenders = [
        (rule.rule_id, pattern)
        for rule, pattern in all_patterns()
        if DEVANAGARI.search(pattern) and BAD_BOUNDARY.search(pattern)
    ]
    assert offenders == [], f"\\b next to Devanagari: {offenders}"


def test_every_pattern_compiles_and_is_not_catastrophic():
    for rule, pattern in all_patterns():
        compiled = re.compile(pattern, re.IGNORECASE | re.DOTALL)
        # A nested unbounded quantifier is the usual source of runaway
        # backtracking; every variable gap in these rules is explicitly bounded.
        assert ".*" not in pattern, f"{rule.rule_id} uses an unbounded gap"
        assert compiled.search("") is None or pattern.startswith("^")


def test_patterns_do_not_match_empty_or_whitespace():
    for rule, pattern in all_patterns():
        compiled = re.compile(pattern, re.IGNORECASE | re.DOTALL)
        for text in ("", " ", "\n", "...", "1234"):
            match = compiled.search(text)
            assert match is None or match.group(0).strip(), f"{rule.rule_id} matched {text!r}"


@pytest.mark.parametrize(
    "phrase",
    [
        "स्कैन करें",
        "सत्यापन करें",
        "भुगतान करें",
        "कॉल करें",
        "अपडेट करें",
    ],
)
def test_scam_instructions_do_not_trigger_the_advisory_guard(phrase):
    """"<verb> करें" is an instruction, not advice: the guard must stay silent."""

    from app.data.scam_rules import RULES_BY_ID

    guard = RULES_BY_ID["GUARD_ADVISORY"]
    assert not any(pattern.search(phrase) for pattern in guard.compiled), phrase


def test_language_tags_match_the_pattern_scripts():
    for rule in SCAM_SIGNAL_RULES:
        has_devanagari = any(DEVANAGARI.search(pattern) for pattern in rule.patterns)
        if has_devanagari:
            assert "hi" in rule.languages, f"{rule.rule_id} has Devanagari but no 'hi' tag"
