from __future__ import annotations

"""Report export and citizen reporting tests (Phase 6.5 and 6.6).

The citizen-reporting tests matter most: that endpoint is the single exception
to the ADR-001 "Citizen Mode persists nothing" rule, so its consent gate is
load-bearing and pinned here.
"""

import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import create_app

OFFICER_USERNAME = "report_officer"
OFFICER_PASSWORD = "ReportTestPassword123"

SCAM_SMS = (
    "Your SBI KYC will be blocked in 24 hours. Verify at https://sbi-verify-kyc.in/urgent "
    "or call 9876543210. Pay to rajesh@okaxis"
)


@pytest.fixture()
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    db_path = tmp_path / f"reports_{uuid.uuid4().hex}.db"

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
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


@pytest.fixture()
def case_id(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post(
        "/api/v1/investigate/submit",
        headers=headers,
        json={"artifact_type": "MESSAGE", "content": SCAM_SMS},
    )
    assert response.status_code == 201
    return response.json()["case_id"]


# --- HTML report ----------------------------------------------------------


def test_report_requires_authentication(client: TestClient, case_id: str) -> None:
    assert client.get(f"/api/v1/investigate/cases/{case_id}/report").status_code == 401


def test_full_report_contains_the_evidence(client: TestClient, headers: dict[str, str], case_id: str) -> None:
    response = client.get(f"/api/v1/investigate/cases/{case_id}/report", headers=headers)
    assert response.status_code == 200
    body = response.text

    assert case_id in body
    assert "Investigation Report" in body
    assert "FULL INVESTIGATION COPY" in body
    assert "rajesh@okaxis" in body
    assert "+919876543210" in body


def test_redacted_report_masks_identifiers(client: TestClient, headers: dict[str, str], case_id: str) -> None:
    """The shareable copy must not leak phone numbers or payment accounts."""

    response = client.get(
        f"/api/v1/investigate/cases/{case_id}/report", headers=headers, params={"redacted": "true"}
    )
    body = response.text

    assert "REDACTED COPY" in body
    assert "rajesh@okaxis" not in body
    assert "9876543210" not in body
    assert "REDACTED" in body


def test_report_states_its_limitations(client: TestClient, headers: dict[str, str], case_id: str) -> None:
    body = client.get(f"/api/v1/investigate/cases/{case_id}/report", headers=headers).text
    assert "not proof of criminal conduct" in body
    assert "1930" in body


def test_report_escapes_html_in_evidence(client: TestClient, headers: dict[str, str]) -> None:
    """Analysed content is untrusted and must never execute inside a report."""

    hostile = "Click <script>alert('xss')</script> now at https://evil.test/go to claim"
    created = client.post(
        "/api/v1/investigate/submit",
        headers=headers,
        json={"artifact_type": "MESSAGE", "content": hostile},
    ).json()["case_id"]

    body = client.get(f"/api/v1/investigate/cases/{created}/report", headers=headers).text
    assert "<script>alert(" not in body
    assert "&lt;script&gt;" in body


def test_unknown_case_report_returns_404(client: TestClient, headers: dict[str, str]) -> None:
    assert (
        client.get("/api/v1/investigate/cases/PRK-20200101-ZZZZZZ/report", headers=headers).status_code
        == 404
    )


# --- JSON and CSV exports -------------------------------------------------


def test_json_export_is_structured_and_complete(
    client: TestClient, headers: dict[str, str], case_id: str
) -> None:
    response = client.get(f"/api/v1/investigate/cases/{case_id}/report.json", headers=headers)
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]

    payload = response.json()
    assert payload["case_id"] == case_id
    assert payload["export_mode"] == "FULL"
    assert payload["findings"] and payload["identifiers"]


def test_redacted_json_masks_identifier_values(
    client: TestClient, headers: dict[str, str], case_id: str
) -> None:
    payload = client.get(
        f"/api/v1/investigate/cases/{case_id}/report.json",
        headers=headers,
        params={"redacted": "true"},
    ).json()
    assert payload["export_mode"] == "REDACTED"
    assert all("rajesh@okaxis" not in item["value"] for item in payload["identifiers"])


def test_cases_csv_export(client: TestClient, headers: dict[str, str], case_id: str) -> None:
    response = client.get("/api/v1/investigate/export/cases.csv", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "case_id,artifact_type,risk_level" in response.text
    assert case_id in response.text


def test_identifiers_csv_lists_every_identifier(
    client: TestClient, headers: dict[str, str], case_id: str
) -> None:
    response = client.get("/api/v1/investigate/export/identifiers.csv", headers=headers)
    assert "rajesh@okaxis" in response.text
    assert "+919876543210" in response.text


def test_csv_export_respects_filters(client: TestClient, headers: dict[str, str], case_id: str) -> None:
    client.post(
        "/api/v1/investigate/submit",
        headers=headers,
        json={"artifact_type": "MESSAGE", "content": "Meeting rescheduled to Tuesday afternoon"},
    )
    filtered = client.get(
        "/api/v1/investigate/export/cases.csv", headers=headers, params={"risk_level": "HIGH"}
    ).text
    assert case_id in filtered
    assert "Meeting rescheduled" not in filtered


def test_csv_export_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/investigate/export/cases.csv").status_code == 401


# --- citizen reporting (ADR-001 exception) --------------------------------


def test_citizen_report_without_consent_is_rejected(client: TestClient) -> None:
    """The consent gate is the whole safeguard; without it nothing is stored."""

    response = client.post(
        "/api/v1/parakh/report-to-police",
        json={"artifact_type": "MESSAGE", "content": SCAM_SMS, "consent": False},
    )
    assert response.status_code == 422
    assert "consent" in response.json()["detail"].lower()


def test_citizen_report_without_consent_stores_nothing(
    client: TestClient, headers: dict[str, str]
) -> None:
    before = client.get("/api/v1/investigate/cases", headers=headers).json()["total"]
    client.post(
        "/api/v1/parakh/report-to-police",
        json={"artifact_type": "MESSAGE", "content": SCAM_SMS, "consent": False},
    )
    after = client.get("/api/v1/investigate/cases", headers=headers).json()["total"]
    assert after == before


def test_citizen_report_with_consent_creates_a_case(
    client: TestClient, headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/v1/parakh/report-to-police",
        json={"artifact_type": "MESSAGE", "content": SCAM_SMS, "consent": True},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["reference"].startswith("PRK-")
    assert body["helpline"] == "1930"

    detail = client.get(
        f"/api/v1/investigate/cases/{body['reference']}", headers=headers
    ).json()
    assert detail["source"] == "CITIZEN"
    assert detail["status"] == "NEW"


def test_citizen_report_needs_no_login(client: TestClient) -> None:
    """Citizens have no account; reporting must work anonymously."""

    response = client.post(
        "/api/v1/parakh/report-to-police",
        json={"artifact_type": "MESSAGE", "content": SCAM_SMS, "consent": True},
    )
    assert response.status_code == 201


def test_plain_citizen_analysis_still_persists_nothing(
    client: TestClient, headers: dict[str, str]
) -> None:
    """The ADR-001 guarantee must survive the reporting feature being added."""

    before = client.get("/api/v1/investigate/cases", headers=headers).json()["total"]
    analysis = client.post("/api/v1/parakh/analyze", json={"message": SCAM_SMS, "language": "en"})
    after = client.get("/api/v1/investigate/cases", headers=headers).json()["total"]

    assert analysis.status_code == 200
    assert after == before


