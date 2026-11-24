from __future__ import annotations

"""Cross-source linking, similarity, and heat-list tests (Phase 5).

These exercise PS01's central premise: the same phone number, UPI ID or domain
appearing in a message, an app and a website should surface as one connected
picture rather than three unrelated reports.
"""

import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import create_app

OFFICER_USERNAME = "link_officer"
OFFICER_PASSWORD = "LinkTestPassword123"


@pytest.fixture()
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    db_path = tmp_path / f"links_{uuid.uuid4().hex}.db"

    def settings_override() -> Settings:
        return Settings(
            database_url=f"sqlite+aiosqlite:///{db_path.as_posix()}",
            officer_username=OFFICER_USERNAME,
            officer_password=OFFICER_PASSWORD,
            gemini_api_key=None,
            enable_offline_fallback=True,
            domain_age_enabled=False,
            redirect_following_enabled=False,
            url_tls_probe_enabled=False,
            rate_limit_requests=1_000,
        )

    monkeypatch.setattr("app.main.get_settings", settings_override)
    monkeypatch.setattr("app.config.get_settings", settings_override)

    app = create_app()
    app.dependency_overrides[get_settings] = settings_override
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/investigate/auth/login",
        json={"username": OFFICER_USERNAME, "password": OFFICER_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


def submit(client: TestClient, headers: dict[str, str], content: str) -> str:
    response = client.post(
        "/api/v1/investigate/submit",
        headers=headers,
        json={"artifact_type": "MESSAGE", "content": content},
    )
    assert response.status_code == 201, response.text
    return response.json()["case_id"]


SHARED_UPI = "Send the fee to fraudster@ybl immediately to release your prize"
SAME_UPI_DIFFERENT_TEXT = "Investment plan: deposit to fraudster@ybl for 10 percent daily returns"
UNRELATED = "Your Amazon order 11223344 has shipped and arrives Tuesday"


# --- linking --------------------------------------------------------------


def test_cases_sharing_a_upi_id_are_linked(client: TestClient, headers: dict[str, str]) -> None:
    first = submit(client, headers, SHARED_UPI)
    second = submit(client, headers, SAME_UPI_DIFFERENT_TEXT)

    linked = client.get(f"/api/v1/investigate/cases/{first}/linked", headers=headers).json()
    assert second in {row["case"]["case_id"] for row in linked}


def test_link_reports_which_identifier_connected_the_cases(
    client: TestClient, headers: dict[str, str]
) -> None:
    first = submit(client, headers, SHARED_UPI)
    submit(client, headers, SAME_UPI_DIFFERENT_TEXT)

    linked = client.get(f"/api/v1/investigate/cases/{first}/linked", headers=headers).json()
    shared = linked[0]["shared_identifiers"]
    assert any("fraudster@ybl" in item for item in shared)


def test_unrelated_case_is_not_linked(client: TestClient, headers: dict[str, str]) -> None:
    first = submit(client, headers, SHARED_UPI)
    unrelated = submit(client, headers, UNRELATED)

    linked = client.get(f"/api/v1/investigate/cases/{first}/linked", headers=headers).json()
    assert unrelated not in {row["case"]["case_id"] for row in linked}


def test_payment_identifier_outranks_a_weak_shared_link(
    client: TestClient, headers: dict[str, str]
) -> None:
    """A shared UPI ID must rank above a merely shared domain."""

    anchor = submit(
        client, headers, "Pay fraudster@ybl now, details at https://common-host.test/a"
    )
    strong = submit(client, headers, "Deposit to fraudster@ybl for guaranteed profit")
    weak = submit(client, headers, "See https://common-host.test/b for details")

    linked = client.get(f"/api/v1/investigate/cases/{anchor}/linked", headers=headers).json()
    ranking = [row["case"]["case_id"] for row in linked]
    assert strong in ranking and weak in ranking
    assert ranking.index(strong) < ranking.index(weak)


def test_case_with_no_identifiers_has_no_links(client: TestClient, headers: dict[str, str]) -> None:
    lonely = submit(client, headers, "Just checking in about the meeting tomorrow afternoon")
    linked = client.get(f"/api/v1/investigate/cases/{lonely}/linked", headers=headers).json()
    assert linked == []


def test_linked_endpoint_requires_authentication(client: TestClient, headers: dict[str, str]) -> None:
    case_id = submit(client, headers, SHARED_UPI)
    assert client.get(f"/api/v1/investigate/cases/{case_id}/linked").status_code == 401


# --- similarity -----------------------------------------------------------


def test_same_template_with_different_numbers_is_an_exact_match(
    client: TestClient, headers: dict[str, str]
) -> None:
    """Campaign detection: one template, different amounts."""

    first = submit(client, headers, "Your KYC will be blocked in 24 hours. Pay 500 to continue.")
    second = submit(client, headers, "Your KYC will be blocked in 48 hours. Pay 900 to continue.")

    similar = client.get(f"/api/v1/investigate/cases/{first}/similar", headers=headers).json()
    matches = {row["case"]["case_id"]: row["match_type"] for row in similar}
    assert matches.get(second) == "EXACT_TEMPLATE"


def test_reworded_variant_is_a_near_duplicate(client: TestClient, headers: dict[str, str]) -> None:
    first = submit(
        client,
        headers,
        "Dear customer your bank account will be suspended today, verify your KYC immediately now",
    )
    second = submit(
        client,
        headers,
        "Dear customer your bank account will be suspended today, verify your KYC right away now",
    )
    similar = client.get(f"/api/v1/investigate/cases/{first}/similar", headers=headers).json()
    assert second in {row["case"]["case_id"] for row in similar}


def test_unrelated_content_is_not_similar(client: TestClient, headers: dict[str, str]) -> None:
    first = submit(client, headers, "Your KYC will be blocked in 24 hours. Pay 500 to continue.")
    unrelated = submit(client, headers, UNRELATED)
    similar = client.get(f"/api/v1/investigate/cases/{first}/similar", headers=headers).json()
    assert unrelated not in {row["case"]["case_id"] for row in similar}


def test_similarity_reports_distance_and_score(client: TestClient, headers: dict[str, str]) -> None:
    first = submit(client, headers, "Your KYC will be blocked in 24 hours. Pay 500 to continue.")
    submit(client, headers, "Your KYC will be blocked in 48 hours. Pay 900 to continue.")
    row = client.get(f"/api/v1/investigate/cases/{first}/similar", headers=headers).json()[0]
    assert row["distance"] == 0
    assert row["similarity"] == 100


# --- identifier pivot -----------------------------------------------------


def test_identifier_pivot_returns_every_case_containing_it(
    client: TestClient, headers: dict[str, str]
) -> None:
    first = submit(client, headers, SHARED_UPI)
    second = submit(client, headers, SAME_UPI_DIFFERENT_TEXT)

    response = client.get(
        "/api/v1/investigate/identifiers/UPI/cases",
        headers=headers,
        params={"value": "fraudster@ybl"},
    )
    assert response.status_code == 200
    found = {row["case_id"] for row in response.json()["cases"]}
    assert {first, second} <= found


def test_identifier_pivot_for_unknown_value_is_empty(
    client: TestClient, headers: dict[str, str]
) -> None:
    response = client.get(
        "/api/v1/investigate/identifiers/UPI/cases",
        headers=headers,
        params={"value": "nobody@nowhere"},
    )
    assert response.json()["total"] == 0


# --- heat-list ------------------------------------------------------------


def test_heatlist_ranks_the_most_reported_identifier_first(
    client: TestClient, headers: dict[str, str]
) -> None:
    for _ in range(3):
        submit(client, headers, f"Pay hotupi@ybl now, reference {uuid.uuid4().hex[:8]}")
    submit(client, headers, "Pay coldupi@okaxis once only")

    entries = client.get(
        "/api/v1/investigate/heatlist", headers=headers, params={"type": "UPI"}
    ).json()
    assert entries
    assert entries[0]["value"] == "hotupi@ybl"
    assert entries[0]["case_count"] == 3


def test_heatlist_can_filter_by_identifier_type(client: TestClient, headers: dict[str, str]) -> None:
    submit(client, headers, "Call 9876543210 and pay hotupi@ybl today")
    entries = client.get(
        "/api/v1/investigate/heatlist", headers=headers, params={"type": "PHONE"}
    ).json()
    assert entries
    assert all(row["type"] == "PHONE" for row in entries)


def test_heatlist_tracks_first_and_last_seen(client: TestClient, headers: dict[str, str]) -> None:
    submit(client, headers, "Pay hotupi@ybl today")
    row = client.get(
        "/api/v1/investigate/heatlist", headers=headers, params={"type": "UPI"}
    ).json()[0]
    assert row["first_seen"] and row["last_seen"]
    assert row["recent_case_count"] >= 1


def test_heatlist_is_empty_on_a_fresh_database(client: TestClient, headers: dict[str, str]) -> None:
    assert client.get("/api/v1/investigate/heatlist", headers=headers).json() == []


def test_heatlist_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/investigate/heatlist").status_code == 401


# --- pre-click warning (citizen-facing) -----------------------------------


def test_precheck_warns_about_a_previously_reported_host(
    client: TestClient, headers: dict[str, str]
) -> None:
    submit(client, headers, "Visit https://reported-scam.test/win to claim your prize")

    response = client.post(
        "/api/v1/parakh/check-before-open", json={"url": "https://reported-scam.test/win"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["previously_reported"] >= 1
    assert body["should_warn"] is True
    assert any("previously reported" in reason for reason in body["reasons"])


def test_precheck_needs_no_authentication(client: TestClient) -> None:
    """Citizens use this before opening a link, so it must stay anonymous."""

    response = client.post(
        "/api/v1/parakh/check-before-open", json={"url": "https://example.com/"}
    )
    assert response.status_code == 200


def test_precheck_flags_a_structurally_risky_url(client: TestClient) -> None:
    response = client.post(
        "/api/v1/parakh/check-before-open", json={"url": "http://hdfc-kyc-update.xyz/login"}
    )
    body = response.json()
    assert body["risk_level"] in {"MEDIUM", "HIGH"}
    assert body["reasons"]

