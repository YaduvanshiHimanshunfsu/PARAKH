from __future__ import annotations

"""Anti-evasion text normalisation with an index map back to the original.

Scammers write ``K.Y.C``, ``KYC`` with Cyrillic letters, ``O​TP`` with a
zero-width space, or ``0TP`` with a digit. Rules match on a *normalised view*
of the message; every match is mapped back to the exact original characters,
so the red-flag phrase the UI highlights is always a real substring of what the
citizen pasted (planversionalpha.md B.1).

Steps, in order:
1. Unicode NFKC (full-width and compatibility characters).
2. Delete zero-width, bidi-control and soft-hyphen characters.
3. Fold Cyrillic/Greek look-alikes to Latin (subset of Unicode TR39
   confusables), only for characters that sit next to Latin letters.
4. Collapse separators inside known acronyms (``K.Y.C`` -> ``KYC``).
5. Fold leetspeak in tokens that become a known keyword (``0TP`` -> ``OTP``).

Devanagari is left untouched: rule packs carry native Devanagari patterns.
"""

import re
import unicodedata
from dataclasses import dataclass

ZERO_WIDTH = frozenset(
    [chr(code) for code in range(0x200B, 0x2010)]  # ZWSP, ZWNJ, ZWJ, LRM, RLM
    + [chr(code) for code in range(0x202A, 0x202F)]  # bidi embeddings/overrides
    + [chr(code) for code in range(0x2066, 0x206A)]  # bidi isolates
    + ["⁠", "﻿", "­", "᠎"]
)

# Unicode TR39 confusables restricted to letters used to disguise Latin words.
CONFUSABLES: dict[str, str] = {
    # Cyrillic lower
    "а": "a", "в": "b", "е": "e", "ё": "e", "к": "k", "м": "m", "н": "h", "о": "o", "р": "p",
    "с": "c", "т": "t", "у": "y", "х": "x", "і": "i", "ї": "i", "ј": "j", "ѕ": "s", "ԁ": "d",
    "ԛ": "q", "ԝ": "w", "һ": "h", "ӏ": "l",
    # Cyrillic upper
    "А": "A", "В": "B", "Е": "E", "Ё": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P",
    "С": "C", "Т": "T", "У": "Y", "Х": "X", "І": "I", "Ї": "I", "Ј": "J", "Ѕ": "S", "Ү": "Y",
    "Ԛ": "Q", "Ԝ": "W",
    # Greek
    "α": "a", "ο": "o", "ν": "v", "ι": "i", "κ": "k", "ρ": "p", "τ": "t", "υ": "u", "χ": "x",
    "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K", "Μ": "M", "Ν": "N",
    "Ο": "O", "Ρ": "P", "Τ": "T", "Υ": "Y", "Χ": "X",
}

KNOWN_ACRONYMS = frozenset(
    {"KYC", "OTP", "UPI", "PIN", "CVV", "ATM", "PAN", "RBI", "CBI", "TRAI", "NCB", "SBI", "EMI", "APK", "SSO", "UTR", "ED"}
)

# Keywords a leet-folded token may become. Kept short and specific so ordinary
# words and numbers are never rewritten.
LEET_KEYWORDS = frozenset(
    {"otp", "kyc", "upi", "pin", "cvv", "bank", "block", "blocked", "account", "verify", "update", "police",
     "arrest", "refund", "reward", "lottery", "winner", "prize", "loan", "password", "login", "paytm", "free",
     "click", "link", "aadhaar", "apk", "urgent", "sbi", "hdfc", "icici"}
)
LEET_MAP = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s", "|": "l"})
LEET_ALT = str.maketrans({"1": "l"})

_ACRONYM = re.compile(r"(?<![A-Za-z0-9])(?:[A-Za-z][.\-_ *]){1,4}[A-Za-z](?![A-Za-z0-9])")
_LEET_TOKEN = re.compile(r"(?<![\w@])[A-Za-z0-9@$|]*[0-9@$|][A-Za-z0-9@$|]*(?![\w])")


def _is_latin_letter(ch: str) -> bool:
    return ch.isascii() and ch.isalpha()


def _script_of(ch: str) -> str:
    try:
        name = unicodedata.name(ch)
    except ValueError:
        return ""
    if name.startswith(("CYRILLIC", "GREEK")):
        return "MIXED"
    if name.startswith("LATIN"):
        return "LATIN"
    return ""


@dataclass(frozen=True)
class NormalisedText:
    """A matching view of a message plus a map back to the original."""

    original: str
    text: str
    index_map: tuple[int, ...]

    def to_original_span(self, start: int, end: int) -> tuple[int, int]:
        if not self.index_map or start >= end:
            return (0, 0)
        start = max(0, min(start, len(self.index_map) - 1))
        end = max(start + 1, min(end, len(self.index_map)))
        return self.index_map[start], self.index_map[end - 1] + 1

    def original_phrase(self, start: int, end: int) -> str:
        s, e = self.to_original_span(start, end)
        return self.original[s:e]


def _base_pass(text: str) -> tuple[list[str], list[int]]:
    """Steps 1-3: NFKC, delete invisible characters, fold confusables."""

    chars: list[str] = []
    index: list[int] = []
    for i, ch in enumerate(text):
        if ch in ZERO_WIDTH:
            continue
        for nch in unicodedata.normalize("NFKC", ch):
            if nch in ZERO_WIDTH:
                continue
            chars.append(nch)
            index.append(i)

    # Fold Cyrillic/Greek look-alikes only inside words that also contain Latin
    # letters or are entirely look-alikes (e.g. "КYС"), never in real Russian
    # or Greek prose surrounded by other non-Latin letters.
    n = len(chars)
    latin_total = sum(1 for c in chars if _is_latin_letter(c))
    foreign_total = sum(1 for c in chars if _script_of(c) == "MIXED")
    mostly_latin = latin_total > foreign_total
    word_start = 0
    while word_start < n:
        if not chars[word_start].isalnum():
            word_start += 1
            continue
        word_end = word_start
        while word_end < n and (chars[word_end].isalnum()):
            word_end += 1
        word = chars[word_start:word_end]
        has_latin = any(_is_latin_letter(c) for c in word)
        foreign = [c for c in word if _script_of(c) == "MIXED"]
        all_foldable = foreign and all(c in CONFUSABLES for c in foreign)
        if foreign and all_foldable and (has_latin or (mostly_latin and len(foreign) <= 6)):
            for k in range(word_start, word_end):
                chars[k] = CONFUSABLES.get(chars[k], chars[k])
        word_start = word_end
    return chars, index


def _rewrite(chars: list[str], index: list[int], pattern: re.Pattern[str], replace) -> tuple[list[str], list[int]]:
    """Apply a regex rewrite while keeping the index map aligned."""

    text = "".join(chars)
    out_chars: list[str] = []
    out_index: list[int] = []
    cursor = 0
    for match in pattern.finditer(text):
        replacement = replace(match)
        if replacement is None:
            continue
        out_chars.extend(chars[cursor:match.start()])
        out_index.extend(index[cursor:match.start()])
        source = index[match.start():match.end()]
        # Spread the replacement over the source span: each output character
        # maps to a source character, and the last maps to the span's end.
        for k, ch in enumerate(replacement):
            out_chars.append(ch)
            out_index.append(source[min(len(source) - 1, round(k * (len(source) - 1) / max(1, len(replacement) - 1)))])
        cursor = match.end()
    out_chars.extend(chars[cursor:])
    out_index.extend(index[cursor:])
    return out_chars, out_index


def _collapse_acronym(match: re.Match[str]) -> str | None:
    letters = re.sub(r"[.\-_ *]", "", match.group(0))
    if letters.upper() in KNOWN_ACRONYMS and letters != match.group(0):
        return letters
    return None


def _fold_leet(match: re.Match[str]) -> str | None:
    token = match.group(0)
    if token.isdigit() or not any(c.isalpha() for c in token):
        return None
    for table in (LEET_MAP, LEET_ALT):
        folded = token.translate(table)
        if folded.lower() in LEET_KEYWORDS:
            return folded if not token.isupper() else folded.upper()
    folded = token.translate(LEET_MAP)
    return folded if folded.lower() in LEET_KEYWORDS else None


def normalise(text: str) -> NormalisedText:
    chars, index = _base_pass(text or "")
    chars, index = _rewrite(chars, index, _ACRONYM, _collapse_acronym)
    chars, index = _rewrite(chars, index, _LEET_TOKEN, _fold_leet)
    return NormalisedText(original=text or "", text="".join(chars), index_map=tuple(index))


def find(pattern: re.Pattern[str], view: NormalisedText) -> tuple[str, int, int] | None:
    """Search the normalised view; return (original phrase, start, end) in the original."""

    match = pattern.search(view.text)
    if not match or match.start() == match.end():
        return None
    s, e = view.to_original_span(match.start(), match.end())
    return view.original[s:e], s, e


__all__ = ["NormalisedText", "normalise", "find", "ZERO_WIDTH", "CONFUSABLES", "KNOWN_ACRONYMS"]
