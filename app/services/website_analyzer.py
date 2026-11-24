from __future__ import annotations

"""Fetch and analyse a suspicious website's content.

PS01 requires examining promotional content for guaranteed returns, MLM
language and betting indicators, and extracting payment identifiers from the
page. None of that is possible without fetching, so this service exists
separately from ``url_intelligence`` rather than loosening the citizen-facing
no-fetch guarantee (DECISIONS.md ADR-002).

Safety constraints, all mandatory:

* SSRF guard re-applied at **every** redirect hop, not just the first
* hard byte cap enforced while streaming, so a huge body is abandoned early
* total timeout, capped redirects, HTML/text content types only
* no JavaScript execution, no subresource loading, no form submission
* the page is never rendered — only parsed as text

A JS-rendered page returns little text. That is reported as a limitation
rather than being allowed to look like a clean result.
"""

import logging
import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

import httpx

from app.config import Settings
from app.data.website_rules import (
    LEGITIMACY_MARKERS,
    MONEY_SOLICITATION,
    WEBSITE_RULES,
)
from app.schemas import (
    AnalysisBundle,
    ArtifactType,
    Finding,
    Identifier,
    IdentifierType,
    RiskLevel,
    ScamCategory,
    Severity,
)
from app.services.identifier_extractor import extract_identifiers, merge_identifiers
from app.services.url_enrichment import PinnedResolverTransport, validate_and_pin
from app.utils.fingerprint import content_hash, simhash

logger = logging.getLogger(__name__)

_MAX_BODY_BYTES = 2_000_000
_FETCH_TIMEOUT_SECONDS = 10.0
_MAX_REDIRECTS = 3
_ALLOWED_CONTENT_TYPES = ("text/html", "text/plain", "application/xhtml+xml")
_SNAPSHOT_CHARS = 20_000
_THIN_CONTENT_CHARS = 400

# A neutral, honest agent string. It must not impersonate a browser, and must
# not leak anything about the operator or the person running the analysis.
_USER_AGENT = "PARAKH-Investigation/1.0 (+static content analysis; no JavaScript)"

_WHITESPACE_RE = re.compile(r"\s+")


class WebsiteFetchError(RuntimeError):
    """The page could not be retrieved safely."""


@dataclass
class FetchedPage:
    url: str
    final_url: str
    status_code: int
    content_type: str
    title: str | None
    text: str
    html_bytes: int
    hops: list[str] = field(default_factory=list)
    truncated: bool = False
    links: list[str] = field(default_factory=list)
    form_fields: list[str] = field(default_factory=list)


class WebsiteAnalyzer:
    """Deterministic content analysis for fraudulent investment/betting sites."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    # --- fetching ----------------------------------------------------------

    async def fetch(self, url: str) -> FetchedPage:
        """Retrieve a page under strict safety limits.

        Redirects are followed manually so the SSRF guard runs on each hop; a
        server that redirects a public hostname to 127.0.0.1 is stopped here.
        """

        current = url if "://" in url else f"https://{url}"
        hops: list[str] = []

        # Pin every validated hop to its resolved public IP so httpx cannot be
        # steered to a private address by DNS rebinding after the safety check.
        pin_map: dict[str, str] = {}
        async with httpx.AsyncClient(
            timeout=_FETCH_TIMEOUT_SECONDS,
            follow_redirects=False,
            max_redirects=0,
            headers={"User-Agent": _USER_AGENT, "Accept": "text/html,text/plain"},
            transport=PinnedResolverTransport(pin_map),
        ) as client:
            for _ in range(_MAX_REDIRECTS + 1):
                safe, reason, pinned = await validate_and_pin(current)
                if not safe:
                    raise WebsiteFetchError(reason or "The address is not safe to fetch.")
                hop_host = urlsplit(current).hostname
                if pinned and hop_host:
                    pin_map[hop_host] = pinned
                hops.append(current)

                try:
                    async with client.stream("GET", current) as response:
                        if 300 <= response.status_code < 400:
                            location = response.headers.get("location")
                            if not location:
                                raise WebsiteFetchError("The site redirected without a destination.")
                            await response.aclose()
                            current = str(httpx.URL(current).join(location))
                            continue

                        content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
                        if content_type and not any(
                            content_type.startswith(allowed) for allowed in _ALLOWED_CONTENT_TYPES
                        ):
                            raise WebsiteFetchError(
                                f"The address returned '{content_type}', which is not a readable web page."
                            )

                        chunks: list[bytes] = []
                        total = 0
                        truncated = False
                        async for chunk in response.aiter_bytes(65_536):
                            total += len(chunk)
                            if total > _MAX_BODY_BYTES:
                                truncated = True
                                break
                            chunks.append(chunk)
                        raw = b"".join(chunks)

                    return self._build_page(
                        url, current, response.status_code, content_type, raw, hops, truncated
                    )
                except httpx.HTTPError as exc:
                    raise WebsiteFetchError(
                        f"The site could not be reached ({type(exc).__name__})."
                    ) from exc

        raise WebsiteFetchError("The site exceeded the redirect limit without returning a page.")

    def _build_page(
        self,
        original: str,
        final: str,
        status: int,
        content_type: str,
        raw: bytes,
        hops: list[str],
        truncated: bool,
    ) -> FetchedPage:
        markup = raw.decode("utf-8", "replace")
        title, text, links, fields = self._parse(markup)
        return FetchedPage(
            url=original,
            final_url=final,
            status_code=status,
            content_type=content_type or "unknown",
            title=title,
            text=text,
            html_bytes=len(raw),
            hops=hops,
            truncated=truncated,
            links=links,
            form_fields=fields,
        )

    @staticmethod
    def _parse(markup: str) -> tuple[str | None, str, list[str], list[str]]:
        """Extract visible text, title, links and form field names.

        BeautifulSoup is already a dependency for email parsing. Nothing is
        rendered and no subresource is fetched.
        """

        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(markup, "html.parser")
            for tag in soup(["script", "style", "noscript", "template"]):
                tag.decompose()
            title = soup.title.string.strip()[:300] if soup.title and soup.title.string else None
            text = soup.get_text(" ", strip=True)
            links = [
                str(a.get("href"))[:500]
                for a in soup.find_all("a", href=True)[:300]
            ]
            fields = [
                str(i.get("name") or i.get("id") or i.get("type"))[:80]
                for i in soup.find_all(["input", "select", "textarea"])[:100]
            ]
        except Exception:
            # Never let a malformed page break the analysis.
            title = None
            text = re.sub(r"<[^>]+>", " ", markup)
            links = []
            fields = []

        # Meta description and alt text often carry the pitch; keep the raw
        # markup's visible attributes out, but normalise whitespace.
        return title, _WHITESPACE_RE.sub(" ", text).strip()[:200_000], links, fields

    # --- analysis ----------------------------------------------------------

    def analyze_page(self, page: FetchedPage) -> AnalysisBundle:
        """Score fetched content against the reviewed website rules."""

        haystack = f"{page.title or ''} {page.text}"
        findings: list[Finding] = []
        score = 0
        categories: list[ScamCategory] = []

        for rule in WEBSITE_RULES:
            match = rule.pattern.search(haystack)
            if not match:
                continue
            findings.append(
                Finding(
                    code=rule.code,
                    severity=rule.severity,
                    explanation=rule.explanation,
                    evidence=self._evidence_window(haystack, match.start(), match.end()),
                )
            )
            score += rule.weight
            categories.append(rule.category)

        identifiers = self._identifiers(page)
        payment_findings, payment_score = self._payment_findings(identifiers)
        findings.extend(payment_findings)
        score += payment_score

        legitimacy_findings, legitimacy_score = self._legitimacy_findings(page, haystack)
        findings.extend(legitimacy_findings)
        score += legitimacy_score

        if page.truncated:
            findings.append(
                Finding(
                    code="PAGE_TRUNCATED",
                    severity=Severity.LOW,
                    explanation=(
                        "The page exceeded the inspection size limit, so only its first portion was "
                        "analysed."
                    ),
                    evidence=None,
                )
            )

        score = max(0, min(100, score))
        limitations = self._limitations(page)

        return AnalysisBundle(
            artifact_type=ArtifactType.WEBSITE,
            risk_level=self._risk_level(score),
            risk_score=score,
            verdict=None,
            summary=self._summary(page, score, categories),
            findings=findings[:60],
            identifiers=identifiers,
            content_text=self._snapshot(page),
            content_sha256=content_hash(page.text) if page.text else None,
            simhash=simhash(page.text) if page.text else None,
            details={
                "url": page.url,
                "final_url": page.final_url,
                "status_code": page.status_code,
                "content_type": page.content_type,
                "title": page.title,
                "html_bytes": page.html_bytes,
                "redirect_hops": page.hops,
                "text_length": len(page.text),
                "link_count": len(page.links),
                "form_fields": page.form_fields[:40],
                "dominant_category": (
                    max(set(categories), key=categories.count).value if categories else None
                ),
                "limitations": limitations,
            },
        )

    async def analyze(self, url: str) -> AnalysisBundle:
        page = await self.fetch(url)
        return self.analyze_page(page)

    # --- helpers -----------------------------------------------------------

    @staticmethod
    def _evidence_window(text: str, start: int, end: int, window: int = 70) -> str:
        left = max(0, start - window)
        right = min(len(text), end + window)
        prefix = "…" if left > 0 else ""
        suffix = "…" if right < len(text) else ""
        return f"{prefix}{text[left:right].strip()}{suffix}"[:500]

    def _identifiers(self, page: FetchedPage) -> list[Identifier]:
        """Harvest payment and contact identifiers — the money trail PS01 wants."""

        from_text = extract_identifiers(page.text, include_context=True)
        # Links carry UPI deep links and Telegram invites that visible text may not.
        from_links = extract_identifiers("\n".join(page.links), include_context=False)
        merged = merge_identifiers(from_text, from_links)

        upi_links = [link for link in page.links if link.lower().startswith("upi:")]
        for link in upi_links:
            query = urlsplit(link).query
            match = re.search(r"pa=([^&]+)", query)
            if match:
                value = match.group(1).lower()
                merged = merge_identifiers(
                    merged,
                    [
                        Identifier(
                            type=IdentifierType.UPI,
                            value=value,
                            raw_value=link[:512],
                            context="UPI payment link on page",
                            confidence=100,
                        )
                    ],
                )
        return merged

    @staticmethod
    def _payment_findings(identifiers: list[Identifier]) -> tuple[list[Finding], int]:
        findings: list[Finding] = []
        score = 0

        grouped: dict[IdentifierType, list[str]] = {}
        for item in identifiers:
            grouped.setdefault(item.type, []).append(item.value)

        payment_types = {
            IdentifierType.UPI: "UPI ID",
            IdentifierType.BANK_ACCOUNT: "bank account number",
            IdentifierType.IFSC: "IFSC code",
            IdentifierType.CRYPTO_BTC: "Bitcoin address",
            IdentifierType.CRYPTO_ETH: "Ethereum/USDT address",
        }
        present = {kind: grouped[kind] for kind in payment_types if kind in grouped}
        if present:
            listed = "; ".join(
                f"{payment_types[kind]}: {', '.join(values[:3])}" for kind, values in present.items()
            )
            findings.append(
                Finding(
                    code="PAGE_COLLECTS_PAYMENT_IDENTIFIER",
                    severity=Severity.HIGH,
                    explanation=(
                        "The page publishes payment identifiers that money would be sent to. These "
                        "are directly actionable for tracing and freezing the receiving accounts."
                    ),
                    evidence=listed[:500],
                )
            )
            score += 25

        if IdentifierType.TELEGRAM in grouped:
            findings.append(
                Finding(
                    code="PAGE_TELEGRAM_FUNNEL",
                    severity=Severity.MEDIUM,
                    explanation=(
                        "The page links to Telegram, moving victims to an unmoderated channel where "
                        "the operator controls the conversation."
                    ),
                    evidence=", ".join(grouped[IdentifierType.TELEGRAM][:5]),
                )
            )
            score += 14

        return findings, score

    @staticmethod
    def _legitimacy_findings(page: FetchedPage, haystack: str) -> tuple[list[Finding], int]:
        """On a money-soliciting page, missing basics are themselves a signal."""

        if not MONEY_SOLICITATION.search(haystack):
            return [], 0

        missing = [name for name, pattern in LEGITIMACY_MARKERS if not pattern.search(haystack)]
        if len(missing) < 3:
            return [], 0

        return (
            [
                Finding(
                    code="MISSING_LEGITIMACY_MARKERS",
                    severity=Severity.MEDIUM,
                    explanation=(
                        "The page asks for money but does not publish "
                        f"{', '.join(missing[:4])}. A registered financial business is required to "
                        "disclose these; a disposable fraud site usually does not."
                    ),
                    evidence=f"missing: {', '.join(missing)}",
                )
            ],
            16,
        )

    @staticmethod
    def _limitations(page: FetchedPage) -> list[str]:
        limitations = [
            "The page was fetched as text only. No JavaScript was executed and no form was submitted.",
        ]
        if len(page.text) < _THIN_CONTENT_CHARS:
            limitations.append(
                "Very little readable text was returned. The site may render its content with "
                "JavaScript, so this analysis may not reflect what a visitor actually sees."
            )
        if page.truncated:
            limitations.append("Only the first portion of the page was inspected due to its size.")
        if page.hops and len(page.hops) > 1:
            limitations.append(f"The address redirected {len(page.hops) - 1} time(s) before loading.")
        return limitations

    @staticmethod
    def _snapshot(page: FetchedPage) -> str:
        """Evidence snapshot stored with the case."""

        header = (
            f"URL: {page.url}\n"
            f"Final URL: {page.final_url}\n"
            f"HTTP status: {page.status_code}\n"
            f"Title: {page.title or '(none)'}\n"
            f"---\n"
        )
        return (header + page.text)[:_SNAPSHOT_CHARS]

    @staticmethod
    def _risk_level(score: int) -> RiskLevel:
        if score >= 70:
            return RiskLevel.HIGH
        if score >= 35:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    @staticmethod
    def _summary(page: FetchedPage, score: int, categories: list[ScamCategory]) -> str:
        host = urlsplit(page.final_url).hostname or page.url
        if categories:
            dominant = max(set(categories), key=categories.count).value.replace("_", " ").title()
            return f"{host} — {dominant} indicators, risk score {score}/100"
        return f"{host} — no reviewed fraud indicators matched, risk score {score}/100"
