from __future__ import annotations

"""Content fingerprinting for repeat-content detection.

PS01 asks for "repeat-content and similarity detection". Scam campaigns reuse
one template with the amount, name, or link swapped, so an exact hash alone is
not enough.

Two fingerprints are stored per case:

* ``content_sha256`` — SHA-256 of aggressively normalised text. Digits and URLs
  are masked, so the same template with different amounts collapses to one hash.
* ``simhash`` — a 64-bit locality-sensitive hash. Near-duplicates differ by only
  a few bits, so Hamming distance finds reworded variants an exact hash misses.

SimHash is implemented here rather than pulled in as a dependency: it is ~30
lines and avoids an unmaintained package in the critical path.
"""

import hashlib
import re

_URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
_DIGIT_RUN_RE = re.compile(r"\d+")
_NON_WORD_RE = re.compile(r"[^\w\s]", re.UNICODE)
_WHITESPACE_RE = re.compile(r"\s+")

_SIMHASH_BITS = 64
_SHINGLE_SIZE = 5

# Masking placeholders. Chosen so the punctuation-stripping pass leaves them
# intact and no genuine message is likely to contain them.
NUM_TOKEN = "numtoken"
URL_TOKEN = "urltoken"


def normalise_for_hashing(text: str) -> str:
    """Strip the parts a scammer varies between sends of the same template.

    Placeholders are deliberately unlikely words rather than ``<num>``: the
    punctuation pass that follows would reduce bracketed markers to ``num``,
    which a real message could contain.
    """

    lowered = text.casefold()
    lowered = _URL_RE.sub(f" {URL_TOKEN} ", lowered)
    lowered = _DIGIT_RUN_RE.sub(f" {NUM_TOKEN} ", lowered)
    lowered = _NON_WORD_RE.sub(" ", lowered)
    return _WHITESPACE_RE.sub(" ", lowered).strip()


def content_hash(text: str) -> str:
    """SHA-256 of the normalised text — exact template match."""

    return hashlib.sha256(normalise_for_hashing(text).encode("utf-8")).hexdigest()


def _shingles(text: str) -> list[str]:
    """Overlapping character n-grams.

    Character n-grams, not word shingles. A scam SMS is short, so word-level
    shingles are far too brittle: swapping one word in an 80-character message
    changes 5 of roughly 10 word-shingles, which measured at distance 34 —
    indistinguishable from entirely unrelated text at 35-41. The same edit
    touches only a handful of character n-grams, which keeps reworded variants
    well separated from unrelated messages.
    """

    if len(text) >= _SHINGLE_SIZE:
        return [text[i: i + _SHINGLE_SIZE] for i in range(len(text) - _SHINGLE_SIZE + 1)]
    return [text] if text else []


def simhash(text: str) -> str:
    """64-bit SimHash of the normalised text, as 16 hex characters."""

    normalised = normalise_for_hashing(text)
    shingles = _shingles(normalised)
    if not shingles:
        return "0" * 16

    vector = [0] * _SIMHASH_BITS
    for shingle in shingles:
        digest = hashlib.blake2b(shingle.encode("utf-8"), digest_size=8).digest()
        value = int.from_bytes(digest, "big")
        for bit in range(_SIMHASH_BITS):
            vector[bit] += 1 if (value >> bit) & 1 else -1

    fingerprint = 0
    for bit in range(_SIMHASH_BITS):
        if vector[bit] > 0:
            fingerprint |= 1 << bit
    return f"{fingerprint:016x}"


def hamming_distance(left: str, right: str) -> int:
    """Bit difference between two SimHash hex strings. Lower means more similar."""

    try:
        return bin(int(left, 16) ^ int(right, 16)).count("1")
    except (ValueError, TypeError):
        return _SIMHASH_BITS


# Measured on representative scam text with character 5-gram shingling:
# reworded variants of one message land at 8-14 bits, while unrelated messages
# start at 26. A threshold of 16 keeps a 10-bit margin before the nearest
# unrelated match.
NEAR_DUPLICATE_THRESHOLD = 16


def is_near_duplicate(left: str, right: str, threshold: int = NEAR_DUPLICATE_THRESHOLD) -> bool:
    return hamming_distance(left, right) <= threshold
