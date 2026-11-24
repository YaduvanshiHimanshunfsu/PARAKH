from __future__ import annotations

"""Endpoints added for the new frontend (planversionalpha.md H.6).

Each one replaces a number the Stitch mock-ups invented with a real value.
"""

import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import create_app

OFFICER = ("test_officer", "InvestigationPass123")
PONZI = (
    "RichPlan Investment: Guaranteed 10% daily returns! Referral bonus on every downline member. "
    "Joining package Rs 5000. Pay richplan@ybl or call 9812345670."
)


@pytest.fixture()
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    db_path = tmp_path / f"cases_{uuid.uuid4().hex}.db"

    def settings_override() -> Settings:
        return Settings(
            database_url=f"sqlite+aiosqlite:///{db_path.as_posix()}",
            officer_username=OFFICER[0],
            officer_password=OFFICER[1],
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


def auth(client: TestClient) -> dict[str, str]:
    response = client.post("/api/v1/investigate/auth/login", json={"username": OFFICER[0], "password": OFFICER[1]})
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_meta_reports_real_engine_facts(client: TestClient) -> None:
    body = client.get("/api/v1/parakh/meta").json()
    from app.data.scam_rules import SCAM_SIGNAL_RULES

    assert body["rule_count"] == len(SCAM_SIGNAL_RULES)
    assert "KYC_SCAM" in body["scam_categories"]
    assert body["ai_configured"] is False


def test_identifier_check_unknown_value_is_low_with_honest_limitation(client: TestClient) -> None:
    body = client.post("/api/v1/parakh/identifier/check", json={"value": "someone@okaxis"}).json()
    assert body["type"] == "UPI"
    assert body["risk_level"] == "LOW"
    assert body["reported_case_count"] == 0
    assert "does not mean the identifier is safe" in body["limitations"]


def test_identifier_check_counts_officer_cases_but_not_citizen_reports(client: TestClient) -> None:
    headers = auth(client)
    # Anonymous citizen reports must not make an identifier look "reported".
    for _ in range(3):
        client.post(
            "/api/v1/parakh/report-to-police",
            json={"artifact_type": "MESSAGE", "content": PONZI, "consent": True},
        )
    assert client.post("/api/v1/parakh/identifier/check", json={"value": "richplan@ybl"}).json()["reported_case_count"] == 0

    created = client.post("/api/v1/investigate/submit", json={"artifact_type": "MESSAGE", "content": PONZI}, headers=headers)
    assert created.json()["risk_level"] == "HIGH"
    body = client.post("/api/v1/parakh/identifier/check", json={"value": "richplan@ybl"}).json()
    assert body["reported_case_count"] == 1
    assert body["risk_level"] == "MEDIUM"


def test_identifier_check_normalises_phone_input(client: TestClient) -> None:
    body = client.post("/api/v1/parakh/identifier/check", json={"value": "+91 98123 45670"}).json()
    assert body["type"] == "PHONE"
    assert body["value"] == "+919812345670"


def test_identifier_check_with_nothing_recognisable(client: TestClient) -> None:
    body = client.post("/api/v1/parakh/identifier/check", json={"value": "hello there"}).json()
    assert body["type"] is None
    assert "No UPI ID" in body["limitations"]


def test_dashboard_summary_is_computed_from_cases(client: TestClient) -> None:
    headers = auth(client)
    assert client.get("/api/v1/investigate/dashboard/summary").status_code == 401
    empty = client.get("/api/v1/investigate/dashboard/summary?days=7", headers=headers).json()
    assert empty["total_cases"] == 0 and len(empty["series"]) == 7

    client.post("/api/v1/investigate/submit", json={"artifact_type": "MESSAGE", "content": PONZI}, headers=headers)
    client.post("/api/v1/investigate/submit", json={"artifact_type": "URL", "content": "https://sbi-verify-kyc.in/urgent"}, headers=headers)
    body = client.get("/api/v1/investigate/dashboard/summary?days=7", headers=headers).json()
    assert body["total_cases"] == 2
    assert body["new_today"] == 2
    assert body["artifact_mix"] == {"MESSAGE": 1, "URL": 1}
    assert sum(point["high"] + point["medium"] + point["low"] for point in body["series"]) == 2
    assert len(body["recent_cases"]) == 2


def test_mine_filter_returns_only_own_submissions(client: TestClient) -> None:
    headers = auth(client)
    client.post("/api/v1/parakh/report-to-police", json={"artifact_type": "MESSAGE", "content": PONZI, "consent": True})
    client.post("/api/v1/investigate/submit", json={"artifact_type": "MESSAGE", "content": PONZI}, headers=headers)
    assert client.get("/api/v1/investigate/cases", headers=headers).json()["total"] == 2
    mine = client.get("/api/v1/investigate/cases?mine=true", headers=headers).json()
    assert mine["total"] == 1 and mine["cases"][0]["source"] == "OFFICER"


def test_heatlist_entries_carry_previous_week_count(client: TestClient) -> None:
    headers = auth(client)
    client.post("/api/v1/investigate/submit", json={"artifact_type": "MESSAGE", "content": PONZI}, headers=headers)
    entries = client.get("/api/v1/investigate/heatlist", headers=headers).json()
    assert entries and all("previous_case_count" in entry for entry in entries)
