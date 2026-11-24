from __future__ import annotations

"""Extract actionable identifiers from any untrusted text.

PS01 requires pulling UPI IDs, bank details, phone numbers, crypto wallets and
app identifiers out of messages, APK strings and website content, then linking
the same identifier across all three. This module is the single extractor all
analysers share so a phone number found in an SMS normalises identically to one
found inside a DEX string.

Design notes
------------
* Matching is span-based. Every pattern reports its character range, and
  overlaps are resolved by specificity so ``9876543210`` inside a URL is not
  also reported as a phone number.
* Normalisation is the whole point. Linking only works if ``+91 98765 43210``
  and ``9876543210`` collapse to one value.
* Precision beats recall. A false UPI match pollutes the heat-list for every
  later case, so ambiguous patterns require corroborating context.
"""

import ipaddress
import re
from dataclasses import dataclass
from typing import Callable, Iterable

from app.schemas import Identifier, IdentifierType

_CONTEXT_WINDOW = 60
_MAX_IDENTIFIERS = 300

# UPI handles have no dot after the '@'; email domains always do. That single
# structural difference separates the two far more reliably than a handle list.
# The list below only raises confidence for handles we positively recognise.
KNOWN_PSP_HANDLES = frozenset({
    "okaxis", "okhdfcbank", "okicici", "oksbi", "ybl", "ibl", "axl", "apl",
    "paytm", "upi", "airtel", "freecharge", "fbl", "kotak", "indus", "sbi",
    "hdfcbank", "icici", "icicibank", "axisbank", "barodampay", "cnrb", "pnb",
    "idfcbank", "yesbank", "yespay", "federal", "rbl", "dbs", "jio", "jupiteraxis",
    "abfspay", "naviaxis", "pingpay", "postbank", "mahb", "uco", "utbi", "psb",
    "kbl", "tjsb", "unionbankofindia", "uboi", "ubi", "idbi", "indianbank",
    "iob", "csbpay", "equitas", "fincare", "ausfb", "esfb", "jkb", "slice",
    "sliceaxis", "timecosmos", "waaxis", "wasbi", "wahdfcbank", "waicici",
    "superyes", "seyes", "tapicici", "goaxb", "omni", "rapl", "yapl", "aubank",
})

# First-segment hints that a dotted token is an Android package, not a hostname.
_PACKAGE_PREFIXES = frozenset({
    "com", "in", "org", "net", "io", "co", "app", "me", "dev", "xyz", "ru", "cn", "uk",
})

_BANK_CONTEXT = re.compile(
    r"(?:a/?c|acc(?:oun)?t|acct|beneficiary|benificiary|ifsc|bank|deposit|transfer|neft|rtgs|imps)",
    re.IGNORECASE,
)

# A label written directly before a number. "A/c 918273645501" is an account
# whose digits happen to fit the "91 + mobile" shape.
_ACCOUNT_LABEL = re.compile(
    r"(?:\ba/?c|\bacc(?:oun)?t|\bacct|\bbeneficiary)(?:\s*(?:no|number|num))?\.?\s*[:#\-]?\s*$",
    re.IGNORECASE,
)

# Tokens that look like Indian mobile numbers but are structurally something
# else. Checked against the surrounding text, not the number itself.
_NON_PHONE_CONTEXT = re.compile(r"(?:order|invoice|txn|transaction|ref(?:erence)?|utr|pin\s*code)", re.IGNORECASE)

# Dotted quads inside a version string are not network addresses.
_VERSION_CONTEXT = re.compile(r"(?:version|v\d|build|release|sdk|schema)\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class _Span:
    start: int
    end: int
    type: IdentifierType
    raw: str
    value: str
    confidence: int
    specificity: int


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value)


# --- normalisers -----------------------------------------------------------

def _normalise_phone(raw: str) -> str:
    digits = _digits(raw)
    if len(digits) > 10 and digits.startswith("91"):
        digits = digits[2:]
    if len(digits) > 10 and digits.startswith("0"):
        digits = digits.lstrip("0")
    return f"+91{digits[-10:]}"


def _normalise_url(raw: str) -> str:
    value = raw.strip().rstrip(".,;:!?)\"']")
    if "://" not in value:
        value = f"https://{value}"
    return value.lower()


def _normalise_domain(raw: str) -> str:
    return raw.strip().rstrip(".").lower()


# --- pattern table ---------------------------------------------------------
#
# specificity breaks overlap ties: a longer, more structured match wins. A URL
# (90) beats a bare domain (50) which beats a digit run (20).

_PATTERNS: tuple[tuple[IdentifierType, re.Pattern[str], int, int, Callable[[str], str]], ...] = (
    (
        IdentifierType.URL,
        re.compile(r"\b(?:https?://|www\.)[^\s<>\"'`]{3,2000}", re.IGNORECASE),
        95,
        100,
        _normalise_url,
    ),
    (
        IdentifierType.EMAIL,
        re.compile(r"\b[A-Za-z0-9._%+\-]{1,64}@[A-Za-z0-9.\-]{1,200}\.[A-Za-z]{2,24}\b"),
        90,
        100,
        lambda raw: raw.strip().lower(),
    ),
    (
        IdentifierType.TELEGRAM,
        # Ranked above URL: for an investigator a t.me handle is the actionable
        # identifier, and reporting it as a generic link loses that.
        re.compile(r"\b(?:https?://)?t\.me/(?:joinchat/)?[A-Za-z0-9_+\-]{3,64}\b", re.IGNORECASE),
        92,
        110,
        lambda raw: raw.strip().lower().replace("https://", "").replace("http://", ""),
    ),
    (
        IdentifierType.CRYPTO_ETH,
        re.compile(r"\b0x[a-fA-F0-9]{40}\b"),
        96,
        100,
        lambda raw: raw.strip().lower(),
    ),
    (
        IdentifierType.CRYPTO_BTC,
        re.compile(r"\b(?:bc1[ac-hj-np-z02-9]{11,71}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b"),
        94,
        90,
        lambda raw: raw.strip(),
    ),
    (
        IdentifierType.IFSC,
        re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b"),
        88,
        95,
        lambda raw: raw.strip().upper(),
    ),
    (
        IdentifierType.UPI,
        re.compile(r"\b[A-Za-z0-9][A-Za-z0-9.\-_]{1,63}@[A-Za-z]{2,24}\b"),
        70,
        70,
        lambda raw: raw.strip().lower(),
    ),
    (
        IdentifierType.PHONE,
        # The trailing guard rejects a longer digit run or a dotted-decimal
        # continuation, but must still allow a number ending a sentence.
        re.compile(r"(?<![\d@])(?<!\d\.)(?:\+?91[\s\-]?)?[6-9]\d{4}[\s\-]?\d{5}(?![\d@])(?!\.\d)"),
        75,
        90,
        _normalise_phone,
    ),
    (
        IdentifierType.IP,
        re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])"),
        75,
        95,
        lambda raw: raw.strip(),
    ),
    (
        IdentifierType.PACKAGE,
        re.compile(r"\b[a-z][a-z0-9_]{1,30}(?:\.[a-z0-9_]{1,30}){2,6}\b"),
        65,
        70,
        lambda raw: raw.strip().lower(),
    ),
    (
        IdentifierType.DOMAIN,
        re.compile(
            r"\b(?:[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?\.)+"
            r"(?:com|in|net|org|co|io|xyz|top|click|link|info|biz|online|site|app|shop|live|club|vip|win|bet|me|ru|cn|uk|us|tk|ml|gq|work|pro)\b",
            re.IGNORECASE,
        ),
        50,
        80,
        _normalise_domain,
    ),
    (
        IdentifierType.BANK_ACCOUNT,
        # Gated on nearby banking context in _accept, so an accepted match is
        # already corroborated and does not deserve a low score.
        re.compile(r"(?<!\d)\d{9,18}(?!\d)"),
        70,
        60,
        lambda raw: raw.strip(),
    ),
)


# --- per-type validation ---------------------------------------------------

def _accept(kind: IdentifierType, raw: str, value: str, text: str, start: int, end: int) -> tuple[bool, int]:
    """Return (accepted, confidence_delta). Rejects structurally wrong matches."""

    window = text[max(0, start - _CONTEXT_WINDOW): end + _CONTEXT_WINDOW]

    if kind is IdentifierType.UPI:
        handle = value.rsplit("@", 1)[1]
        # An email was already matched at higher specificity; anything with a
        # dotted right-hand side is a mail domain, not a UPI handle.
        if "." in handle:
            return False, 0
        return True, 25 if handle in KNOWN_PSP_HANDLES else -10

    if kind is IdentifierType.IP:
        try:
            parsed = ipaddress.ip_address(raw)
        except ValueError:
            return False, 0
        # Keep only routable addresses: private/loopback ranges are noise in a
        # scam report, and a dotted quad after "version"/"build" is not an IP.
        if parsed.is_private or parsed.is_loopback or parsed.is_reserved or parsed.is_multicast:
            return False, 0
        if _VERSION_CONTEXT.search(text[max(0, start - 20): start]):
            return False, 0
        return True, 0

    if kind is IdentifierType.PHONE:
        if len(_digits(raw)) not in {10, 11, 12}:
            return False, 0
        if "+" not in raw and _ACCOUNT_LABEL.search(text[max(0, start - 30): start]):
            return False, 0
        if _NON_PHONE_CONTEXT.search(window):
            return True, -25
        return True, 0

    if kind is IdentifierType.BANK_ACCOUNT:
        # A bare digit run is far too common to accept unconditionally.
        return bool(_BANK_CONTEXT.search(window)), 0

    if kind is IdentifierType.PACKAGE:
        segments = value.split(".")
        if segments[0] not in _PACKAGE_PREFIXES:
            return False, 0
        # com.whatsapp is a package; whatsapp.com is a domain. Distinguished by
        # which end carries the TLD-like token.
        if len(segments) < 3:
            return False, 0
        return True, 0

    if kind is IdentifierType.IFSC:
        return value[4] == "0", 0

    return True, 0


def _overlaps(a: _Span, b: _Span) -> bool:
    return a.start < b.end and b.start < a.end


def _context_for(text: str, start: int, end: int) -> str:
    left = max(0, start - _CONTEXT_WINDOW)
    right = min(len(text), end + _CONTEXT_WINDOW)
    snippet = text[left:right].replace("\n", " ").replace("\r", " ")
    snippet = re.sub(r"\s+", " ", snippet).strip()
    prefix = "…" if left > 0 else ""
    suffix = "…" if right < len(text) else ""
    return f"{prefix}{snippet}{suffix}"[:300]


def extract_identifiers(text: str, *, include_context: bool = True) -> list[Identifier]:
    """Extract and de-duplicate every actionable identifier in ``text``."""

    if not text or not text.strip():
        return []

    spans: list[_Span] = []
    for kind, pattern, base_confidence, specificity, normalise in _PATTERNS:
        for match in pattern.finditer(text):
            raw = match.group(0)
            try:
                value = normalise(raw)
            except (IndexError, ValueError):
                continue
            if not value:
                continue
            accepted, delta = _accept(kind, raw, value, text, match.start(), match.end())
            if not accepted:
                continue
            spans.append(
                _Span(
                    start=match.start(),
                    end=match.end(),
                    type=kind,
                    raw=raw[:512],
                    value=value[:512],
                    confidence=max(0, min(100, base_confidence + delta)),
                    specificity=specificity,
                )
            )

    # Resolve overlaps: prefer the more specific pattern, then the longer match.
    spans.sort(key=lambda s: (-s.specificity, -(s.end - s.start), s.start))
    kept: list[_Span] = []
    for span in spans:
        if any(_overlaps(span, existing) for existing in kept):
            continue
        kept.append(span)

    # A URL implies its host; surface that separately so linking works whether a
    # later case cites the full URL or just the domain. An IP-hosted URL yields
    # an IP identifier, not a domain.
    for span in list(kept):
        if span.type is not IdentifierType.URL:
            continue
        host = re.sub(r"^https?://", "", span.value).split("/", 1)[0].split(":", 1)[0]
        host = host.removeprefix("www.")
        if not host or "." not in host:
            continue
        try:
            parsed_host = ipaddress.ip_address(host)
        except ValueError:
            host_type = IdentifierType.DOMAIN
        else:
            if parsed_host.is_private or parsed_host.is_loopback or parsed_host.is_reserved:
                continue
            host_type = IdentifierType.IP
        if not any(k.type is host_type and k.value == host for k in kept):
            kept.append(_Span(span.start, span.end, host_type, host, host, 85, 0))

    kept.sort(key=lambda s: s.start)

    results: list[Identifier] = []
    seen: set[tuple[IdentifierType, str]] = set()
    for span in kept:
        key = (span.type, span.value)
        if key in seen:
            continue
        seen.add(key)
        results.append(
            Identifier(
                type=span.type,
                value=span.value,
                raw_value=span.raw,
                context=_context_for(text, span.start, span.end) if include_context else None,
                confidence=span.confidence,
            )
        )
        if len(results) >= _MAX_IDENTIFIERS:
            break
    return results


def merge_identifiers(*groups: Iterable[Identifier]) -> list[Identifier]:
    """Combine identifier lists from several sources, keeping the best confidence."""

    best: dict[tuple[IdentifierType, str], Identifier] = {}
    for group in groups:
        for item in group:
            key = (item.type, item.value)
            existing = best.get(key)
            if existing is None or item.confidence > existing.confidence:
                best[key] = item
    return list(best.values())[:_MAX_IDENTIFIERS]
