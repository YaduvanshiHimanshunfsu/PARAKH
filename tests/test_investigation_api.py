from __future__ import annotations

"""Integration tests for Investigation Mode (Phases 1 and 2).

Covers the officer auth gate, the submit â†’ persist â†’ search â†’ retrieve loop,
and the ADR-001 guarantee that Citizen Mode writes nothing to the case store.
"""

import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import create_app

OFFICER_USERNAME = "test_officer"
OFFICER_PASSWORD = "InvestigationPass123"


@pytest.fixture()
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    """App bound to a throwaway SQLite file with a seeded officer account."""

    db_path = tmp_path / f"cases_{uuid.uuid4().hex}.db"

    def settings_override() -> Settings:
        return Settings(
            database_url=f"sqlite+aiosqlite:///{db_path.as_posix()}",
            officer_username=OFFICER_USERNAME,
            officer_password=OFFICER_PASSWORD,
            gemini_api_key=None,
            enable_offline_fallback=True,
            # Network enrichment is disabled so tests are deterministic and
            # never depend on RDAP or a live redirect target.
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


def auth_header(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/investigate/auth/login",
        json={"username": OFFICER_USERNAME, "password": OFFICER_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


SCAM_SMS = (
    "Dear customer your SBI KYC will be blocked in 24 hours. "
    "Verify at https://sbi-verify-kyc.in/urgent or call 9876543210. Pay to rajesh@okaxis"
)


# --- authentication --------------------------------------------------------


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/v1/investigate/cases"),
        ("get", "/api/v1/investigate/cases/PRK-20260101-ABCDEF"),
        ("post", "/api/v1/investigate/submit"),
        ("get", "/api/v1/investigate/me"),
    ],
)
def test_investigation_routes_reject_anonymous_access(client: TestClient, method: str, path: str) -> None:
    if method == "post":
        response = client.post(path, json={"artifact_type": "MESSAGE", "content": "test message"})
    else:
        response = client.get(path)
    assert response.status_code == 401


def test_login_rejects_wrong_password_without_revealing_the_user(client: TestClient) -> None:
    wrong_password = client.post(
        "/api/v1/investigate/auth/login",
        json={"username": OFFICER_USERNAME, "password": "WrongPassword123"},
    )
    unknown_user = client.post(
        "/api/v1/investigate/auth/login",
        json={"username": "nobody_here", "password": "WrongPassword123"},
    )
    assert wrong_password.status_code == 401
    assert unknown_user.status_code == 401
    # Identical message: the response must not enumerate valid usernames.
    assert wrong_password.json()["detail"] == unknown_user.json()["detail"]


def test_login_succeeds_and_identifies_the_officer(client: TestClient) -> None:
    headers = auth_header(client)
    response = client.get("/api/v1/investigate/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["username"] == OFFICER_USERNAME


def test_garbage_token_is_rejected(client: TestClient) -> None:
    response = client.get(
        "/api/v1/investigate/cases", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


def test_logout_revokes_the_token(client: TestClient) -> None:
    headers = auth_header(client)
    assert client.post("/api/v1/investigate/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/investigate/cases", headers=headers).status_code == 401


# --- submission and persistence -------------------------------------------


def test_submitting_a_scam_message_opens_a_case_with_reasons(client: TestClient) -> None:
    headers = auth_header(client)
    response = client.post(
        "/api/v1/investigate/submit",
        headers=headers,
        json={"artifact_type": "MESSAGE", "content": SCAM_SMS},
    )
    assert response.status_code == 201, response.text
    body = response.json()

    assert body["case_id"].startswith("PRK-")
    assert body["risk_level"] == "HIGH"
    assert body["findings"], "a risk level without reasons is not explainable"
    assert body["status"] == "NEW"


def test_submission_extracts_the_actionable_identifiers(client: TestClient) -> None:
    headers = auth_header(client)
    body = client.post(
        "/api/v1/investigate/submit",
        headers=headers,
        json={"artifact_type": "MESSAGE", "content": SCAM_SMS},
    ).json()

    found = {(item["type"], item["value"]) for item in body["identifiers"]}
    assert ("PHONE", "+919876543210") in found
    assert ("UPI", "rajesh@okaxis") in found
    assert ("DOMAIN", "sbi-verify-kyc.in") in found


def test_blacklisted_identifier_is_reported_with_its_source(client: TestClient) -> None:
    """A blacklist hit must surface as a finding that names where it came from."""

    import asyncio

    from app.db.models import BlacklistEntry

    database = client.app.state.database

    async def seed_entry() -> None:
        async with database.session() as session:
            session.add(
                BlacklistEntry(
                    type="DOMAIN",
                    value="sbi-verify-kyc.in",
                    source="Demo dataset",
                    reason="Reported SBI KYC phishing host.",
                )
            )

    asyncio.run(seed_entry())

    headers = auth_header(client)
    body = client.post(
        "/api/v1/investigate/submit",
        headers=headers,
        json={"artifact_type": "MESSAGE", "content": SCAM_SMS},
    ).json()

    codes = {finding["code"] for finding in body["findings"]}
    assert "BLACKLIST_MATCH" in codes
    match = next(f for f in body["findings"] if f["code"] == "BLACKLIST_MATCH")
    assert "Demo dataset" in match["explanation"]


def test_identical_template_produces_the_same_content_hash(client: TestClient) -> None:
    """Two sends of one template differing only in amount must collapse to one hash."""

    from app.utils.fingerprint import content_hash

    first = "Your KYC will be blocked in 24 hours. Pay 500 now."
    second = "Your KYC will be blocked in 48 hours. Pay 900 now."
    assert content_hash(first) == content_hash(second)


# --- retrieval -------------------------------------------------------------


def test_case_is_retrievable_and_searchable(client: TestClient) -> None:
    headers = auth_header(client)
    case_id = client.post(
        "/api/v1/investigate/submit",
        headers=headers,
        json={"artifact_type": "MESSAGE", "content": SCAM_SMS},
    ).json()["case_id"]

    detail = client.get(f"/api/v1/investigate/cases/{case_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["case_id"] == case_id

    listing = client.get("/api/v1/investigate/cases", headers=headers).json()
    assert listing["total"] >= 1
    assert case_id in {row["case_id"] for row in listing["cases"]}


def test_search_matches_an_extracted_identifier(client: TestClient) -> None:
    """Searching a UPI ID must find the case it was extracted from."""

    headers = auth_header(client)
    case_id = client.post(
        "/api/v1/investigate/submit",
        headers=headers,
        json={"artifact_type": "MESSAGE", "content": SCAM_SMS},
    ).json()["case_id"]

    results = client.get(
        "/api/v1/investigate/cases", headers=headers, params={"q": "rajesh@okaxis"}
    ).json()
    assert case_id in {row["case_id"] for row in results["cases"]}


def test_risk_level_filter_excludes_other_levels(client: TestClient) -> None:
    headers = auth_header(client)
    client.post(
        "/api/v1/investigate/submit",
        headers=headers,
        json={"artifact_type": "MESSAGE", "content": SCAM_SMS},
    )
    results = client.get(
        "/api/v1/investigate/cases", headers=headers, params={"risk_level": "HIGH"}
    ).json()
    assert results["cases"]
    assert all(row["risk_level"] == "HIGH" for row in results["cases"])


def test_unknown_case_returns_404(client: TestClient) -> None:
    headers = auth_header(client)
    response = client.get("/api/v1/investigate/cases/PRK-20200101-ZZZZZZ", headers=headers)
    assert response.status_code == 404


def test_officer_can_update_status_and_notes(client: TestClient) -> None:
    headers = auth_header(client)
    case_id = client.post(
        "/api/v1/investigate/submit",
        headers=headers,
        json={"artifact_type": "MESSAGE", "content": SCAM_SMS},
    ).json()["case_id"]

    updated = client.patch(
        f"/api/v1/investigate/cases/{case_id}",
        headers=headers,
        json={"status": "UNDER_REVIEW", "officer_note": "Linked to an ongoing enquiry."},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "UNDER_REVIEW"
    assert updated.json()["officer_note"] == "Linked to an ongoing enquiry."


def test_deleting_a_case_removes_its_identifiers(client: TestClient) -> None:
    """Foreign keys must actually cascade.

    SQLite ignores foreign keys unless the ``foreign_keys`` pragma is set per
    connection, which left every ``ondelete="CASCADE"`` inert. Orphaned
    identifier rows would keep appearing in the heat-list and could collide
    with a reused case id.
    """

    import asyncio

    from sqlalchemy import func, select

    from app.db.models import CaseRecord, IdentifierRecord

    headers = auth_header(client)
    case_id = client.post(
        "/api/v1/investigate/submit",
        headers=headers,
        json={"artifact_type": "MESSAGE", "content": SCAM_SMS},
    ).json()["case_id"]

    database = client.app.state.database

    async def count_identifiers() -> int:
        async with database.session() as session:
            return (await session.execute(select(func.count(IdentifierRecord.id)))).scalar_one()

    async def delete_case() -> None:
        async with database.session() as session:
            record = (
                await session.execute(select(CaseRecord).where(CaseRecord.case_id == case_id))
            ).scalar_one()
            await session.delete(record)

    assert asyncio.run(count_identifiers()) > 0
    asyncio.run(delete_case())
    assert asyncio.run(count_identifiers()) == 0, "identifiers outlived their case"


def test_unrelated_apks_are_not_reported_as_repeat_content(client: TestClient) -> None:
    """Similarity applies to authored text, not generated metadata.

    Every APK's stored content is the same metadata layout (package, SDK,
    permissions), so hashing it matched a malicious loan app against a benign
    notes app at 66% similarity.
    """

    from tests.apk_fixtures import build_apk

    headers = auth_header(client)
    first = client.post(
        "/api/v1/investigate/apk/analyze",
        headers=headers,
        files={
            "apk": (
                "loan.apk",
                build_apk(
                    package="com.quickcash.instantloan",
                    label="QuickCash Loan",
                    permissions=("android.permission.READ_SMS", "android.permission.INTERNET"),
                ),
                "application/vnd.android.package-archive",
            )
        },
    ).json()["case_id"]

    client.post(
        "/api/v1/investigate/apk/analyze",
        headers=headers,
        files={
            "apk": (
                "notes.apk",
                build_apk(
                    package="com.example.simplenotes",
                    label="Simple Notes",
                    permissions=("android.permission.INTERNET",),
                ),
                "application/vnd.android.package-archive",
            )
        },
    )

    similar = client.get(f"/api/v1/investigate/cases/{first}/similar", headers=headers).json()
    assert similar == [], "unrelated apps must not be reported as repeat content"


def test_apk_cannot_be_submitted_as_text(client: TestClient) -> None:
    """APKs are binaries; they must go to /apk/analyze, not the text submit route."""

    headers = auth_header(client)
    response = client.post(
        "/api/v1/investigate/submit",
        headers=headers,
        json={"artifact_type": "APK", "content": "com.example.app"},
    )
    assert response.status_code == 422


# --- APK upload (Phase 3) --------------------------------------------------


def test_apk_upload_requires_authentication(client: TestClient) -> None:
    from tests.apk_fixtures import build_apk

    response = client.post(
        "/api/v1/investigate/apk/analyze",
        files={"apk": ("app.apk", build_apk(), "application/vnd.android.package-archive")},
    )
    assert response.status_code == 401


def test_apk_upload_opens_a_case_with_permission_reasons(client: TestClient) -> None:
    from tests.apk_fixtures import build_apk, build_png

    data = build_apk(
        package="com.quickloan.instant",
        label="QuickLoan Instant",
        target_sdk=22,
        permissions=(
            "android.permission.READ_SMS",
            "android.permission.READ_CONTACTS",
            "android.permission.INTERNET",
        ),
        dex_strings=("http://45.133.1.9/collect", "pay fraudster@ybl"),
        icon_png=build_png(seed=4),
    )
    headers = auth_header(client)
    response = client.post(
        "/api/v1/investigate/apk/analyze",
        headers=headers,
        files={"apk": ("quickloan.apk", data, "application/vnd.android.package-archive")},
    )
    assert response.status_code == 201, response.text
    body = response.json()

    assert body["artifact_type"] == "APK"
    assert body["risk_level"] == "HIGH"
    codes = {f["code"] for f in body["findings"]}
    assert "COMBO_LOAN_APP_HARVESTING" in codes
    assert body["details"]["package"] == "com.quickloan.instant"


def test_apk_identifiers_are_persisted_and_searchable(client: TestClient) -> None:
    """An APK's embedded C2 host must be findable by search, like any identifier."""

    from tests.apk_fixtures import build_apk

    data = build_apk(
        package="com.quickloan.instant",
        label="QuickLoan",
        permissions=("android.permission.INTERNET",),
        dex_strings=("http://45.133.1.9/collect",),
    )
    headers = auth_header(client)
    case_id = client.post(
        "/api/v1/investigate/apk/analyze",
        headers=headers,
        files={"apk": ("q.apk", data, "application/vnd.android.package-archive")},
    ).json()["case_id"]

    results = client.get(
        "/api/v1/investigate/cases", headers=headers, params={"q": "45.133.1.9"}
    ).json()
    assert case_id in {row["case_id"] for row in results["cases"]}


def test_non_apk_upload_is_rejected(client: TestClient) -> None:
    headers = auth_header(client)
    response = client.post(
        "/api/v1/investigate/apk/analyze",
        headers=headers,
        files={"apk": ("notes.txt", b"just some text", "text/plain")},
    )
    assert response.status_code == 422
    assert "Android package" in response.json()["detail"]


def test_empty_upload_is_rejected(client: TestClient) -> None:
    headers = auth_header(client)
    response = client.post(
        "/api/v1/investigate/apk/analyze",
        headers=headers,
        files={"apk": ("empty.apk", b"", "application/vnd.android.package-archive")},
    )
    assert response.status_code == 422


def test_apk_case_links_to_a_message_sharing_the_same_host(client: TestClient) -> None:
    """The PS01 premise: one identifier connecting an APK to an SMS report."""

    from tests.apk_fixtures import build_apk

    headers = auth_header(client)
    apk_case = client.post(
        "/api/v1/investigate/apk/analyze",
        headers=headers,
        files={
            "apk": (
                "q.apk",
                build_apk(package="com.quickloan.instant", dex_strings=("http://45.133.1.9/collect",)),
                "application/vnd.android.package-archive",
            )
        },
    ).json()["case_id"]

    sms_case = client.post(
        "/api/v1/investigate/submit",
        headers=headers,
        json={
            "artifact_type": "MESSAGE",
            "content": "Download our loan app now from http://45.133.1.9/collect for instant cash",
        },
    ).json()["case_id"]

    linked = client.get(
        "/api/v1/investigate/cases", headers=headers, params={"q": "45.133.1.9"}
    ).json()
    found = {row["case_id"] for row in linked["cases"]}
    assert {apk_case, sms_case} <= found


# --- ADR-001 guarantee -----------------------------------------------------


def test_citizen_mode_analysis_persists_nothing(client: TestClient) -> None:
    """The load-bearing privacy test.

    A citizen analysing a message must leave no row in the case store. If this
    ever fails, the dual-mode promise in DECISIONS.md ADR-001 is broken.
    """

    import asyncio

    from sqlalchemy import func, select

    from app.db.models import CaseRecord, IdentifierRecord

    headers = auth_header(client)
    before = client.get("/api/v1/investigate/cases", headers=headers).json()["total"]

    citizen = client.post(
        "/api/v1/parakh/analyze", json={"message": SCAM_SMS, "language": "en"}
    )
    assert citizen.status_code == 200
    assert citizen.json()["verdict"] == "SCAM"

    after = client.get("/api/v1/investigate/cases", headers=headers).json()["total"]
    assert after == before, "Citizen Mode must not create a case"

    database = client.app.state.database

    async def count_identifiers() -> int:
        async with database.session() as session:
            return (await session.execute(select(func.count(IdentifierRecord.id)))).scalar_one()

    assert asyncio.run(count_identifiers()) == 0, "Citizen Mode must not store identifiers"


