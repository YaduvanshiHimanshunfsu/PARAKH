from __future__ import annotations

"""Campaign grouping and the public (Citizen Mode) APK check.

A campaign is every case reachable from every other through a shared operator
identifier or a reworded copy of the same template. The citizen APK check must
give the full static analysis while storing nothing (ADR-001).
"""

import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.data.android_permissions import describe_permissions
from app.main import create_app
from app.services.campaign_service import text_changes
from app.services.link_service import links_cases
from tests.apk_fixtures import build_apk, build_png

OFFICER_USERNAME = "campaign_officer"
OFFICER_PASSWORD = "CampaignTestPass123"
APK_MIME = "application/vnd.android.package-archive"

LOAN_PERMISSIONS = (
    "android.permission.READ_SMS",
    "android.permission.RECEIVE_SMS",
    "android.permission.READ_CONTACTS",
    "android.permission.INTERNET",
    "android.permission.SYSTEM_ALERT_WINDOW",
)


@pytest.fixture()
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    db_path = tmp_path / f"campaigns_{uuid.uuid4().hex}.db"

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


def campaigns(client: TestClient, headers: dict[str, str]) -> dict:
    response = client.get("/api/v1/investigate/campaigns", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


PONZI_V1 = (
    "RichPlan Investment: Guaranteed 10% daily returns! Referral bonus on every downline "
    "member. Joining package Rs 5000. Pay richplan@ybl or call 9812345670."
)
PONZI_V2 = (
    "RichPlan Investment: Guaranteed 12% daily returns! Referral bonus on every downline "
    "member. Joining package Rs 9000. Pay richplan@ybl or call 9812345670."
)
UNRELATED = "Your Amazon order 11223344 has shipped and arrives Tuesday between 10am and 2pm."


# --- pure helpers -----------------------------------------------------------


def test_text_changes_report_the_reworded_figures() -> None:
    changes = text_changes(PONZI_V1, PONZI_V2)
    assert [(c.before, c.after) for c in changes] == [("10%", "12%"), ("5000", "9000")]


def test_identical_text_has_no_changes() -> None:
    assert text_changes(PONZI_V1, PONZI_V1) == []


@pytest.mark.parametrize(
    "type_value,value,expected",
    [
        ("UPI", "richplan@ybl", True),
        ("PHONE", "+919812345670", True),
        ("DOMAIN", "richplan-invest.xyz", True),
        ("DOMAIN", "bit.ly", False),   # shared by thousands of unrelated messages
        ("DOMAIN", "www.t.me", False),
        ("URL", "https://richplan-invest.xyz/join", False),  # its domain already links
        ("IFSC", "HDFC0004567", False),  # a bank branch, not an account
        ("NOT_A_TYPE", "x", False),
    ],
)
def test_only_operator_identifiers_link_cases(type_value: str, value: str, expected: bool) -> None:
    assert links_cases(type_value, value) is expected


def test_permission_profile_explains_and_orders_by_power() -> None:
    rows = describe_permissions(
        [
            "android.permission.INTERNET",
            "android.permission.READ_SMS",
            "android.permission.SYSTEM_ALERT_WINDOW",
            "com.example.permission.C2D_MESSAGE",
            "android.permission.READ_SMS",  # duplicates collapse
        ]
    )
    assert [row["level"] for row in rows] == ["SPECIAL", "DANGEROUS", "NORMAL", "UNKNOWN"]
    sms = next(row for row in rows if row["short"] == "READ_SMS")
    assert "OTP" in sms["description"]
    assert rows[-1]["category"] == "App-defined"


# --- campaigns API ------------------------------------------------------------


def test_campaigns_require_an_officer(client: TestClient) -> None:
    assert client.get("/api/v1/investigate/campaigns").status_code == 401


def test_variants_sharing_a_upi_form_one_campaign_with_a_wording_timeline(
    client: TestClient, headers: dict[str, str]
) -> None:
    first = submit(client, headers, PONZI_V1)
    second = submit(client, headers, PONZI_V2)
    submit(client, headers, UNRELATED)

    graph = campaigns(client, headers)
    assert graph["cases_scanned"] == 3
    assert len(graph["campaigns"]) == 1

    campaign = graph["campaigns"][0]
    assert campaign["case_count"] == 2
    assert campaign["risk_level"] == "HIGH"
    assert {(k["type"], k["value"]) for k in campaign["key_identifiers"]} >= {
        ("UPI", "richplan@ybl"),
        ("PHONE", "+919812345670"),
    }

    timeline = campaign["timeline"]
    assert [entry["case_id"] for entry in timeline] == [first, second]
    assert timeline[1]["variant_of"] == first
    assert {"before": "10%", "after": "12%"} in timeline[1]["changes"]

    case_nodes = {node["case_id"] for node in graph["nodes"] if node["kind"] == "case"}
    assert case_nodes == {first, second}
    kinds = {edge["kind"] for edge in graph["edges"]}
    assert kinds == {"identifier", "similar"}


def test_template_alone_links_messages_with_no_shared_identifier(
    client: TestClient, headers: dict[str, str]
) -> None:
    submit(
        client,
        headers,
        "Dear customer your SBI KYC will be blocked in 24 hours. Verify immediately at "
        "https://sbi-verify-kyc.in/urgent or your account will be suspended.",
    )
    later = submit(
        client,
        headers,
        "Dear customer your SBI KYC will be blocked in 24 hours. Verify immediately at "
        "https://sbi-kyc-update.top/verify or your account will be suspended.",
    )

    (campaign,) = campaigns(client, headers)["campaigns"]
    assert campaign["key_identifiers"] == []
    assert campaign["name"].startswith("Repeated template")
    assert campaign["timeline"][1]["case_id"] == later
    assert "DOMAIN: sbi-kyc-update.top" in campaign["timeline"][1]["new_identifiers"]


def test_a_shared_link_shortener_does_not_merge_unrelated_scams(
    client: TestClient, headers: dict[str, str]
) -> None:
    submit(client, headers, "Your parcel is held at customs. Pay duty now at https://bit.ly/parcel42")
    submit(client, headers, "Electricity will be cut tonight, update your meter at https://bit.ly/meter77")

    assert campaigns(client, headers)["campaigns"] == []


# --- citizen APK check ----------------------------------------------------------


def loan_apk(package: str = "com.fastrupee.credit") -> bytes:
    return build_apk(
        package=package,
        label="FastRupee Credit",
        target_sdk=22,
        permissions=LOAN_PERMISSIONS,
        dex_strings=("http://45.133.1.77/collect",),
        icon_png=build_png(seed=21),
    )


def citizen_check(client: TestClient, data: bytes, name: str = "app.apk"):
    return client.post("/api/v1/parakh/apk/analyze", files={"apk": (name, data, APK_MIME)})


def test_citizen_apk_check_is_anonymous_and_explains_permissions(client: TestClient) -> None:
    response = citizen_check(client, loan_apk())
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["risk_level"] == "HIGH"
    assert "COMBO_LOAN_APP_HARVESTING" in {f["code"] for f in body["findings"]}
    assert body["details"]["package"] == "com.fastrupee.credit"
    profile = {row["short"]: row for row in body["details"]["permission_profile"]}
    assert profile["SYSTEM_ALERT_WINDOW"]["level"] == "SPECIAL"
    assert profile["READ_CONTACTS"]["level"] == "DANGEROUS"
    assert body["advice"][0] == "Do not install this app."
    assert body["helpline"] == "1930"
    assert "content_text" not in body


def test_citizen_apk_check_stores_nothing(client: TestClient, headers: dict[str, str]) -> None:
    assert citizen_check(client, loan_apk()).status_code == 200

    cases = client.get("/api/v1/investigate/cases", headers=headers).json()
    assert cases["total"] == 0


def test_citizen_apk_matching_a_high_risk_case_is_flagged(
    client: TestClient, headers: dict[str, str]
) -> None:
    officer = client.post(
        "/api/v1/investigate/apk/analyze",
        headers=headers,
        files={"apk": ("fastrupee.apk", loan_apk(), APK_MIME)},
    )
    assert officer.status_code == 201
    assert officer.json()["risk_level"] == "HIGH"

    body = citizen_check(client, loan_apk()).json()
    reported = {(item["type"], item["value"]) for item in body["reported_identifiers"]}
    assert ("PACKAGE", "com.fastrupee.credit") in reported
    assert body["findings"][0]["code"] == "MATCHES_REPORTED_APP"
    assert body["risk_level"] == "HIGH"


def test_a_benign_app_seen_by_officers_is_not_called_reported(
    client: TestClient, headers: dict[str, str]
) -> None:
    notes = build_apk(
        package="com.example.simplenotes",
        label="Simple Notes",
        permissions=("android.permission.INTERNET",),
    )
    officer = client.post(
        "/api/v1/investigate/apk/analyze",
        headers=headers,
        files={"apk": ("notes.apk", notes, APK_MIME)},
    )
    assert officer.json()["risk_level"] == "LOW"

    body = citizen_check(client, notes).json()
    assert body["reported_identifiers"] == []
    assert body["risk_level"] == "LOW"


def test_citizen_apk_check_rejects_a_file_that_is_not_an_apk(client: TestClient) -> None:
    response = citizen_check(client, b"%PDF-1.7 not an android package", "invoice.apk")
    assert response.status_code == 422


def test_citizen_apk_check_rejects_an_empty_file(client: TestClient) -> None:
    assert citizen_check(client, b"").status_code == 422
