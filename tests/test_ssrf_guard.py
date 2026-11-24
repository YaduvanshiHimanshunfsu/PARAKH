from __future__ import annotations

"""SSRF guard tests.

This is the highest-severity security control in the project: Phase 4 fetches
attacker-supplied URLs, and a redirect chain is an attacker-controlled sequence.
Validating only the first hop is the classic bypass, so the guard is re-applied
at every hop and pinned here.

These tests make no outbound request for the blocking cases — a literal private
address is rejected before DNS, and an unsupported scheme before anything else.
"""

import asyncio

import pytest

from app.services.url_enrichment import is_safe_target


def safety(url: str) -> tuple[bool, str | None]:
    return asyncio.run(is_safe_target(url))


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/admin",
        "https://127.0.0.1:8443/",
        "http://[::1]/local",
        "http://10.0.0.5/internal",
        "http://172.16.0.1/internal",
        "http://192.168.1.1/router",
        "http://0.0.0.0/",
    ],
)
def test_private_and_loopback_addresses_are_blocked(url: str) -> None:
    safe, reason = safety(url)
    assert safe is False
    assert reason


def test_cloud_metadata_endpoint_is_blocked() -> None:
    """169.254.169.254 serves instance credentials on most cloud providers."""

    safe, reason = safety("http://169.254.169.254/latest/meta-data/iam/security-credentials/")
    assert safe is False
    assert reason


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "gopher://evil.test/_payload",
        "ftp://files.test/secret",
        "dict://127.0.0.1:11211/stat",
        "jar:http://evil.test!/",
    ],
)
def test_non_http_schemes_are_blocked(url: str) -> None:
    safe, reason = safety(url)
    assert safe is False
    assert reason and "scheme" in reason.lower()


def test_url_without_a_hostname_is_blocked() -> None:
    safe, reason = safety("http:///just-a-path")
    assert safe is False
    assert reason


def test_hostname_that_does_not_resolve_publicly_is_blocked() -> None:
    safe, reason = safety("http://this-host-does-not-exist-9z8x7c.invalid/")
    assert safe is False
    assert reason


def test_localhost_by_name_is_blocked() -> None:
    """Blocking literal 127.0.0.1 is not enough; the name must resolve and fail too."""

    safe, _ = safety("http://localhost:8000/api")
    assert safe is False


@pytest.mark.parametrize("url", ["https://example.com/", "http://example.com/path?q=1"])
def test_public_hosts_are_allowed(url: str) -> None:
    """Requires DNS. If this fails, check connectivity before suspecting the guard."""

    safe, reason = safety(url)
    assert safe is True, reason


# --- DNS-rebinding / pinning -----------------------------------------------


def test_validate_and_pin_returns_a_public_ip_for_a_hostname() -> None:
    """A hostname must be pinned to a concrete public IP, not re-resolved later."""

    from app.services.url_enrichment import validate_and_pin

    safe, _, pinned = asyncio.run(validate_and_pin("https://example.com/"))
    assert safe is True
    assert pinned  # a concrete address the caller must connect to
    import ipaddress

    assert ipaddress.ip_address(pinned).is_global


def test_validate_and_pin_needs_no_pin_for_a_literal_public_ip() -> None:
    from app.services.url_enrichment import validate_and_pin

    safe, _, pinned = asyncio.run(validate_and_pin("https://8.8.8.8/"))
    assert safe is True
    assert pinned is None  # already its own connection target


def test_pinned_transport_binds_the_connection_to_the_validated_ip() -> None:
    """The connection must go to the pinned IP even if DNS would now say otherwise.

    Pinning the hostname to a loopback IP must make the connection fail: that
    proves the transport connects to the pin and does not re-resolve the name.
    """

    import httpx

    from app.services.url_enrichment import PinnedResolverTransport

    async def attempt() -> str:
        pin_map = {"example.com": "127.0.0.1"}
        async with httpx.AsyncClient(
            transport=PinnedResolverTransport(pin_map),
            follow_redirects=False,
            timeout=5,
        ) as client:
            try:
                await client.get("https://example.com/")
            except Exception as exc:  # ConnectError / SSL error — never a 200
                return type(exc).__name__
            return "CONNECTED"

    assert asyncio.run(attempt()) != "CONNECTED"
