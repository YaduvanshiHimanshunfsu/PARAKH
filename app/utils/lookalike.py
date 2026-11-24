from __future__ import annotations

"""Look-alike (typosquatting) detection for domain labels.

Two independent checks, both pure Python (planversionalpha.md B.4):

* **Optimal String Alignment distance** (Damerau-Levenshtein with adjacent
  transposition) catches ``sbii``, ``hdfcbnak``, ``icicl``.
* **Confusable skeleton** (a subset of Unicode TR39) catches ``rnicrosoft``
  and digit-for-letter swaps such as ``jvvn1``.

The approach is inspired by dnstwist, but inverted: dnstwist *generates*
permutations of a brand, while PARAKH *tests a given domain* against the
protected list, which is what an incoming URL needs.
"""

from app.data.protected_brands import PROTECTED_LABELS

# Characters that read alike at a glance, folded to one representative.
_SKELETON_MAP = {
    "0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "6": "g", "7": "t", "8": "b", "9": "g",
    "i": "l", "j": "l", "|": "l", "!": "l",
    "q": "g",
    "v": "u",
    "z": "s",
}
# Multi-character sequences that imitate a single letter.
_SKELETON_PAIRS = (("rn", "m"), ("vv", "w"), ("cl", "d"), ("nn", "m"))

MIN_LABEL_LENGTH = 4
MAX_EDIT_DISTANCE = 2


def osa_distance(a: str, b: str, *, cutoff: int = 3) -> int:
    """Optimal String Alignment distance, bounded by ``cutoff``."""

    if a == b:
        return 0
    if abs(len(a) - len(b)) > cutoff:
        return cutoff + 1
    previous2: list[int] = []
    previous = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        current = [i] + [0] * len(b)
        best = current[0]
        for j in range(1, len(b) + 1):
            cost = int(a[i - 1] != b[j - 1])
            value = min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                value = min(value, previous2[j - 2] + 1)
            current[j] = value
            best = min(best, value)
        if best > cutoff:
            return cutoff + 1
        previous2, previous = previous, current
    return previous[len(b)]


def skeleton(label: str) -> str:
    """Fold a label to its visual skeleton so look-alikes collide."""

    text = label.lower()
    for pair, replacement in _SKELETON_PAIRS:
        text = text.replace(pair, replacement)
    return "".join(_SKELETON_MAP.get(ch, ch) for ch in text)


def lookalike_match(label: str) -> tuple[str, str, str] | None:
    """Return ``(protected_label, brand_name, reason)`` for a near-miss label.

    ``None`` when the label is not close to any protected label, or when it
    *is* one (an exact match is the real brand, not an imitation).
    """

    candidate = (label or "").lower().strip("-")
    if len(candidate) < MIN_LABEL_LENGTH or candidate in PROTECTED_LABELS:
        return None

    candidate_skeleton = skeleton(candidate)
    best: tuple[int, str, str, str] | None = None
    for protected, brand in PROTECTED_LABELS.items():
        if abs(len(candidate) - len(protected)) > MAX_EDIT_DISTANCE:
            continue
        if candidate_skeleton == skeleton(protected):
            return protected, brand, "characters that look like other characters"
        distance = osa_distance(candidate, protected, cutoff=MAX_EDIT_DISTANCE)
        if not 1 <= distance <= MAX_EDIT_DISTANCE:
            continue
        # The shorter the real name, the stronger the evidence has to be: one
        # edit on a 3-letter name is common in ordinary words.
        if distance == 2 and len(protected) < 6:
            continue
        if len(protected) < MIN_LABEL_LENGTH and distance > 1:
            continue
        if best is None or distance < best[0]:
            best = (distance, protected, brand, f"{distance} character{'s' if distance > 1 else ''} different")
    if best is None:
        return None
    return best[1], best[2], best[3]


def lookalike_in_tokens(tokens) -> tuple[str, str, str] | None:
    """First look-alike found among a hostname's tokens (longest token first)."""

    for token in sorted(tokens, key=len, reverse=True):
        match = lookalike_match(token)
        if match:
            return match
    return None


__all__ = [
    "osa_distance",
    "skeleton",
    "lookalike_match",
    "lookalike_in_tokens",
    "MIN_LABEL_LENGTH",
    "MAX_EDIT_DISTANCE",
]
