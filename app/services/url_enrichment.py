from __future__ import annotations

"""Investigation-grade URL enrichment: domain age, redirect chains, blacklists.

PS01 names "domain age, redirects, HTTPS status and blacklist matches" under
message and URL analysis. The existing ``url_intelligence`` service deliberately
refuses to follow redirects, so that capability lives here instead of loosening
the citizen-facing guarantee (DECISIONS.md ADR-002).

Every outbound request in this module re-applies the SSRF guard. A redirect
chain is an attacker-controlled sequence: validating only the first hop is the
classic bypass, so each hop is resolved and checked independently.
"""

import asyncio
import ipaddress
import logging
import socket
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models import BlacklistEntry, DomainIntel
from app.schemas import Finding, Identifier, IdentifierType, Severity

logger = logging.getLogger(__name__)

_RDAP_ENDPOINT = "https://rdap.org/domain/{domain}"
_NEW_DOMAIN_DAYS = 30
_YOUNG_DOMAIN_DAYS = 180


@dataclass
class RedirectHop:
    url: str
    status_code: int
    host: str | None = None


@dataclass
class RedirectChain:
    hops: list[RedirectHop] = field(default_factory=list)
    final_url: str | None = None
    blocked_reason: str | None = None
    truncated: bool = False


@dataclass
class DomainAge:
    domain: str
    status: str = "UNKNOWN"
    age_days: int | None = None
    registrar: str | None = None
    registered_on: datetime | None = None


async def _resolve_public_addresses(host: str, port: int = 443) -> list[str]:
    """Resolve a host to globally routable addresses only.

    Returns an empty list for private, loopback, link-local, or reserved
    targets, which callers must treat as "do not connect".
    """

    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, OSError, UnicodeError):
        return []
    addresses: list[str] = []
    for *_, address in infos:
        ip = address[0]
        try:
            parsed = ipaddress.ip_address(ip)
        except ValueError:
            continue
        if parsed.is_global and ip not in addresses:
            addresses.append(ip)
    return addresses


async def is_safe_target(url: str) -> tuple[bool, str | None]:
    """Reject anything that is not an http(s) URL resolving to a public address."""

    parts = urlsplit(url)
    if parts.scheme.lower() not in {"http", "https"}:
        return False, f"Unsupported scheme '{parts.scheme or 'none'}'."
    host = parts.hostname
    if not host:
        return False, "The link has no hostname."

    # A literal private address never needs DNS to be rejected.
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        if not literal.is_global:
            return False, "The link points at a private or reserved address."
        return True, None

    if not await _resolve_public_addresses(host, parts.port or (443 if parts.scheme == "https" else 80)):
        return False, "The hostname does not resolve to a public address."
    return True, None


class UrlEnrichmentService:
    """Domain age, redirect resolution, and blacklist matching for investigations."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    # --- domain age (RDAP) -------------------------------------------------

    async def domain_age(self, domain: str, session: AsyncSession | None = None) -> DomainAge:
        """Look up registration age via RDAP, cached in the database.

        RDAP returns JSON over HTTPS, so there is no WHOIS text to parse and no
        extra dependency. A failure degrades to UNKNOWN rather than failing the
        surrounding analysis.
        """

        domain = domain.strip().lower().rstrip(".")
        if not domain or not self._settings.domain_age_enabled:
            return DomainAge(domain=domain, status="NOT_CHECKED")

        if session is not None:
            cached = await self._cached_domain(session, domain)
            if cached is not None:
                return cached

        result = await self._fetch_rdap(domain)

        if session is not None:
            await self._store_domain(session, result)
        return result

    async def _cached_domain(self, session: AsyncSession, domain: str) -> DomainAge | None:
        row = (
            await session.execute(select(DomainIntel).where(DomainIntel.domain == domain))
        ).scalar_one_or_none()
        if row is None:
            return None
        fetched = row.fetched_at
        if fetched.tzinfo is None:
            fetched = fetched.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - fetched > timedelta(hours=self._settings.domain_intel_cache_hours):
            return None
        # Recompute age from the stored registration date so a cached row does
        # not report a stale age after sitting in the database for days.
        age_days = row.age_days
        if row.registered_on is not None:
            registered = row.registered_on
            if registered.tzinfo is None:
                registered = registered.replace(tzinfo=timezone.utc)
            age_days = (datetime.now(timezone.utc) - registered).days
        return DomainAge(
            domain=row.domain,
            status=row.status,
            age_days=age_days,
            registrar=row.registrar,
            registered_on=row.registered_on,
        )

    async def _store_domain(self, session: AsyncSession, result: DomainAge) -> None:
        row = (
            await session.execute(select(DomainIntel).where(DomainIntel.domain == result.domain))
        ).scalar_one_or_none()
        if row is None:
            row = DomainIntel(domain=result.domain)
            session.add(row)
        row.registrar = result.registrar
        row.registered_on = result.registered_on
        row.age_days = result.age_days
        row.status = result.status
        row.fetched_at = datetime.now(timezone.utc)
        await session.flush()

    async def _fetch_rdap(self, domain: str) -> DomainAge:
        timeout = self._settings.domain_age_timeout_seconds
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.get(
                    _RDAP_ENDPOINT.format(domain=domain),
                    headers={"Accept": "application/rdap+json"},
                )
        except Exception as exc:
            logger.warning("rdap_unavailable domain_suffix=%s error=%s", domain[-12:], type(exc).__name__)
            return DomainAge(domain=domain, status="ERROR")

        if response.status_code == 404:
            return DomainAge(domain=domain, status="NOT_FOUND")
        if response.status_code != 200:
            return DomainAge(domain=domain, status="ERROR")

        try:
            payload = response.json()
        except ValueError:
            return DomainAge(domain=domain, status="ERROR")

        registered_on = self._registration_date(payload)
        registrar = self._registrar(payload)
        age_days = (datetime.now(timezone.utc) - registered_on).days if registered_on else None
        return DomainAge(
            domain=domain,
            status="OK" if registered_on else "NO_DATE",
            age_days=age_days,
            registrar=registrar,
            registered_on=registered_on,
        )

    @staticmethod
    def _registration_date(payload: dict) -> datetime | None:
        for event in payload.get("events", []) or []:
            if str(event.get("eventAction", "")).lower() in {"registration", "registered"}:
                raw = str(event.get("eventDate", ""))
                try:
                    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                except ValueError:
                    continue
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        return None

    @staticmethod
    def _registrar(payload: dict) -> str | None:
        for entity in payload.get("entities", []) or []:
            roles = {str(role).lower() for role in entity.get("roles", []) or []}
            if "registrar" not in roles:
                continue
            for item in entity.get("vcardArray", [None, []])[1] or []:
                if isinstance(item, list) and len(item) >= 4 and item[0] == "fn":
                    return str(item[3])[:256]
        return None

    def domain_age_findings(self, age: DomainAge) -> list[Finding]:
        """A newly registered domain is one of the strongest phishing indicators."""

        if age.age_days is None:
            return []
        if age.age_days <= _NEW_DOMAIN_DAYS:
            return [
                Finding(
                    code="NEWLY_REGISTERED_DOMAIN",
                    severity=Severity.HIGH,
                    explanation=(
                        f"The domain was registered {age.age_days} days ago. Newly created domains are "
                        "heavily used in phishing because they have no history to check."
                    ),
                    evidence=f"{age.domain} registered {age.age_days} days ago",
                )
            ]
        if age.age_days <= _YOUNG_DOMAIN_DAYS:
            return [
                Finding(
                    code="YOUNG_DOMAIN",
                    severity=Severity.MEDIUM,
                    explanation=(
                        f"The domain is {age.age_days} days old. A short history is a risk signal for a site "
                        "asking for money or personal details, though not proof of fraud."
                    ),
                    evidence=f"{age.domain} registered {age.age_days} days ago",
                )
            ]
        return []

    # --- redirect chain ----------------------------------------------------

    async def resolve_redirects(self, url: str) -> RedirectChain:
        """Follow a redirect chain manually, re-checking SSRF safety at each hop."""

        chain = RedirectChain()
        if not self._settings.redirect_following_enabled:
            chain.blocked_reason = "Redirect following is disabled."
            return chain

        current = url if "://" in url else f"https://{url}"
        timeout = self._settings.url_analysis_timeout_seconds

        try:
            async with httpx.AsyncClient(
                timeout=timeout, follow_redirects=False, max_redirects=0
            ) as client:
                for hop_index in range(self._settings.max_redirect_hops):
                    safe, reason = await is_safe_target(current)
                    if not safe:
                        chain.blocked_reason = reason
                        return chain

                    try:
                        response = await client.request("HEAD", current)
                        if response.status_code >= 400:
                            # Some hosts reject HEAD; retry once with a ranged GET.
                            response = await client.get(current, headers={"Range": "bytes=0-0"})
                    except httpx.HTTPError as exc:
                        chain.blocked_reason = f"The link could not be reached ({type(exc).__name__})."
                        return chain

                    host = urlsplit(current).hostname
                    chain.hops.append(
                        RedirectHop(url=current, status_code=response.status_code, host=host)
                    )

                    location = response.headers.get("location")
                    if not (300 <= response.status_code < 400) or not location:
                        chain.final_url = current
                        return chain

                    current = str(httpx.URL(current).join(location))
                else:
                    chain.truncated = True
                    chain.final_url = current
        except Exception as exc:
            logger.warning("redirect_resolution_failed error=%s", type(exc).__name__)
            chain.blocked_reason = "The redirect chain could not be resolved."
        return chain

    @staticmethod
    def redirect_findings(chain: RedirectChain, original_host: str | None) -> list[Finding]:
        findings: list[Finding] = []
        if chain.blocked_reason:
            return findings

        hop_count = max(0, len(chain.hops) - 1)
        if hop_count >= 2:
            findings.append(
                Finding(
                    code="REDIRECT_CHAIN_LONG",
                    severity=Severity.MEDIUM,
                    explanation=(
                        f"The link passes through {hop_count} redirects before reaching its destination. "
                        "Long chains are used to hide the final page from both users and scanners."
                    ),
                    evidence=" → ".join(hop.url for hop in chain.hops)[:500],
                )
            )

        final_host = urlsplit(chain.final_url).hostname if chain.final_url else None
        if original_host and final_host and original_host.lower() != final_host.lower():
            findings.append(
                Finding(
                    code="CROSS_DOMAIN_REDIRECT",
                    severity=Severity.HIGH,
                    explanation=(
                        f"The link starts at {original_host} but ends at {final_host}. "
                        "The visible address is not where you would actually land."
                    ),
                    evidence=f"{original_host} → {final_host}",
                )
            )

        if chain.truncated:
            findings.append(
                Finding(
                    code="REDIRECT_CHAIN_TRUNCATED",
                    severity=Severity.MEDIUM,
                    explanation=(
                        "The redirect chain exceeded the inspection limit, so the true destination "
                        "was not reached. Treat the link as unresolved."
                    ),
                    evidence=None,
                )
            )
        return findings

    # --- blacklist ---------------------------------------------------------

    @staticmethod
    async def match_blacklist(
        session: AsyncSession, identifiers: list[Identifier]
    ) -> list[Finding]:
        """Flag any extracted identifier present in the reviewed blacklist.

        The source of each entry is reported so a match is explainable rather
        than an unexplained verdict.
        """

        if not identifiers:
            return []

        wanted = {(item.type.value, item.value) for item in identifiers}
        rows = (
            (
                await session.execute(
                    select(BlacklistEntry).where(
                        BlacklistEntry.value.in_({value for _, value in wanted})
                    )
                )
            )
            .scalars()
            .all()
        )

        findings: list[Finding] = []
        for row in rows:
            if (row.type, row.value) not in wanted:
                continue
            findings.append(
                Finding(
                    code="BLACKLIST_MATCH",
                    severity=Severity.HIGH,
                    explanation=(
                        f"This {row.type.replace('_', ' ').lower()} appears in the reviewed blacklist "
                        f"({row.source}). {row.reason}".strip()
                    ),
                    evidence=f"{row.type}: {row.value}",
                )
            )
        return findings
