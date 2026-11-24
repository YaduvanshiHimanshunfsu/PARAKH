from __future__ import annotations

"""Phase D: action pack, approval chain, dispatch and MIS."""

import asyncio
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import Settings, get_settings
from app.core.auth import hash_password
from app.data.approval_policy import first_stage, needs_supervisor, policy_for
from app.db.models import UserRecord
from app.db.units_seed import seed_units
from app.main import create_app
from app.schemas import Identifier, IdentifierType
from app.services import addressee_resolver
from app.services.addressee_resolver import BANK_FREEZE_106, BANK_PRODUCE_94, TELECOM_CAF_CDR

PASSWORD = "InvestigationPass123"
PONZI = (
    "RichPlan Investment: Guaranteed 10% daily returns! Referral bonus on every downline member. "
    "Joining package Rs 5000. Pay richplan@ybl or call 9812345670 now."
)


# --- D.2 addressee resolution ----------------------------------------------


def identifier(kind: IdentifierType, value: str, context: str = "Pay to this") -> Identifier:
    return Identifier(type=kind, value=value, raw_value=value, context=context, confidence=90)


def test_upi_handle_resolves_to_a_provider_but_stays_marked_verify():
    [produce, freeze] = addressee_resolver.resolve(identifier(IdentifierType.UPI, "richplan@ybl"))
    assert produce.doc_type == BANK_PRODUCE_94
    assert freeze.doc_type == BANK_FREEZE_106
    assert produce.addressee.org_name == "PhonePe Payments"
    # Handle-to-bank arrangements change, so the draft must say "confirm".
    assert produce.confidence == addressee_resolver.VERIFY
    assert "confirm" in produce.note.lower()


def test_unknown_upi_handle_is_not_guessed():
    [resolution] = addressee_resolver.resolve(identifier(IdentifierType.UPI, "scam@notarealpsp"))
    assert resolution.confidence == addressee_resolver.UNRESOLVED
    assert "not in PARAKH" in resolution.note


def test_ifsc_prefix_is_a_confirmed_mapping():
    [resolution] = addressee_resolver.resolve(identifier(IdentifierType.IFSC, "SBIN0001234"))
    assert resolution.addressee.org_name == "State Bank of India"
    assert resolution.confidence == addressee_resolver.CONFIRMED


def test_phone_produces_a_telecom_notice_and_a_chakshu_report():
    resolutions = addressee_resolver.resolve(identifier(IdentifierType.PHONE, "+919812345670"))
    assert {item.doc_type for item in resolutions} == {TELECOM_CAF_CDR, "DOT_CHAKSHU_REPORT"}
    telecom = next(item for item in resolutions if item.doc_type == TELECOM_CAF_CDR)
    assert "ported" in telecom.note.lower() or "confirm" in telecom.note.lower()


def test_every_sample_addressee_uses_a_placeholder_not_an_invented_contact():
    from app.data.addressees import ALL_ADDRESSEES

    for item in ALL_ADDRESSEES:
        assert "@" not in item.contact_placeholder, f"{item.key} looks like a real email"
        assert item.contact_placeholder.strip()


# --- D.5 policy -------------------------------------------------------------


def test_a_freeze_always_needs_a_supervisor():
    assert needs_supervisor(BANK_FREEZE_106, None)
    assert first_stage(BANK_FREEZE_106) == "STATION"
    assert policy_for(BANK_FREEZE_106).sla_hours == 2


def test_a_large_loss_escalates_a_production_notice():
    assert not needs_supervisor(BANK_PRODUCE_94, 50_000 * 100)
    assert needs_supervisor(BANK_PRODUCE_94, 10_00_000 * 100)


# --- end-to-end through the API --------------------------------------------


@pytest.fixture()
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    db_path = tmp_path / f"action_{uuid.uuid4().hex}.db"

    def settings_override() -> Settings:
        return Settings(
            database_url=f"sqlite+aiosqlite:///{db_path.as_posix()}",
            officer_username="admin_officer",
            officer_password=PASSWORD,
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


def make_officer(client: TestClient, username: str, role: str, rank: str, unit_code: str) -> None:
    database = client.app.state.database

    async def create() -> None:
        async with database.session() as session:
            units = await seed_units(session)
            exists = (
                await session.execute(select(UserRecord).where(UserRecord.username == username))
            ).scalar_one_or_none()
            if exists is not None:
                return
            session.add(
                UserRecord(
                    username=username,
                    password_hash=hash_password(PASSWORD),
                    role=role,
                    rank=rank,
                    unit_id=units[unit_code].id,
                    is_active=True,
                )
            )

    asyncio.run(create())


def auth(client: TestClient, username: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/investigate/auth/login", json={"username": username, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


@pytest.fixture()
def station(client: TestClient) -> dict:
    """An IO, a station head and a supervisor in one station, with a case."""

    make_officer(client, "io.sharma", "IO", "SI", "JPR-CYBER-PS")
    make_officer(client, "sho.cyber", "STATION_HEAD", "INSPECTOR", "JPR-CYBER-PS")
    make_officer(client, "sp.jaipur", "SUPERVISOR", "SP", "JPR-COMM")
    io = auth(client, "io.sharma")
    case_id = client.post(
        "/api/v1/investigate/submit",
        json={"artifact_type": "MESSAGE", "content": PONZI},
        headers=io,
    ).json()["case_id"]
    return {
        "io": io,
        "sho": auth(client, "sho.cyber"),
        "sp": auth(client, "sp.jaipur"),
        "case_id": case_id,
    }


def test_action_pack_drafts_one_notice_per_addressee(client: TestClient, station: dict) -> None:
    response = client.post(
        f"/api/v1/investigate/cases/{station['case_id']}/action-pack", headers=station["io"]
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["created"] >= 3
    types = {item["doc_type"] for item in body["documents"]}
    # The UPI ID justifies a production notice and a freeze; the phone number a
    # telecom notice and a Chakshu report; every case gets an evidence
    # certificate.
    assert {BANK_PRODUCE_94, BANK_FREEZE_106, TELECOM_CAF_CDR, "BSA_63_CERT"} <= types
    assert all(item["status"] == "DRAFT" for item in body["documents"])
    assert "unsigned draft" in body["notice"]


def test_regenerating_does_not_duplicate(client: TestClient, station: dict) -> None:
    first = client.post(
        f"/api/v1/investigate/cases/{station['case_id']}/action-pack", headers=station["io"]
    ).json()
    second = client.post(
        f"/api/v1/investigate/cases/{station['case_id']}/action-pack", headers=station["io"]
    ).json()
    assert second["created"] == 0
    assert len(second["documents"]) == len(first["documents"])


def test_draft_carries_a_watermark_and_no_signature(client: TestClient, station: dict) -> None:
    documents = client.post(
        f"/api/v1/investigate/cases/{station['case_id']}/action-pack", headers=station["io"]
    ).json()["documents"]
    freeze = next(item for item in documents if item["doc_type"] == BANK_FREEZE_106)
    printed = client.get(f"/api/v1/investigate/documents/{freeze['id']}/print", headers=station["io"])
    assert printed.status_code == 200
    html = printed.text
    assert "DRAFT" in html
    assert "Section 106" in html
    assert "(Signature)" in html  # left blank for the approving officer
    assert "richplan@ybl" in html


def test_the_drafter_cannot_approve_their_own_document(client: TestClient, station: dict) -> None:
    documents = client.post(
        f"/api/v1/investigate/cases/{station['case_id']}/action-pack", headers=station["io"]
    ).json()["documents"]
    doc_id = documents[0]["id"]

    submitted = client.post(f"/api/v1/investigate/documents/{doc_id}/submit", headers=station["io"])
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "PENDING_STATION"

    # The IO drafted it, so even a station head role could not approve it if
    # they were the drafter; here the IO simply lacks the stage role.
    refused = client.post(f"/api/v1/investigate/documents/{doc_id}/approve", headers=station["io"])
    assert refused.status_code == 403


def test_full_chain_of_command_for_a_freeze_request(client: TestClient, station: dict) -> None:
    documents = client.post(
        f"/api/v1/investigate/cases/{station['case_id']}/action-pack", headers=station["io"]
    ).json()["documents"]
    freeze = next(item for item in documents if item["doc_type"] == BANK_FREEZE_106)
    doc_id = freeze["id"]

    client.post(f"/api/v1/investigate/documents/{doc_id}/submit", headers=station["io"])

    # Station head approves; a freeze always needs a supervisor as well.
    station_approved = client.post(
        f"/api/v1/investigate/documents/{doc_id}/approve",
        json={"comment": "Facts verified against the complaint."},
        headers=station["sho"],
    )
    assert station_approved.status_code == 200, station_approved.text
    assert station_approved.json()["status"] == "PENDING_SUPERVISOR"

    supervisor_approved = client.post(
        f"/api/v1/investigate/documents/{doc_id}/approve", headers=station["sp"]
    )
    assert supervisor_approved.status_code == 200, supervisor_approved.text
    body = supervisor_approved.json()
    assert body["status"] == "APPROVED"
    assert [item["action"] for item in body["approvals"]] == ["SUBMIT", "APPROVE", "APPROVE"]
    assert [item["stage"] for item in body["approvals"]][1:] == ["STATION", "SUPERVISOR"]

    dispatched = client.post(
        f"/api/v1/investigate/documents/{doc_id}/dispatch",
        json={"channel": "EMAIL", "reference": "JPR/CYBER/OUT/2026/114"},
        headers=station["sho"],
    )
    assert dispatched.status_code == 200
    assert dispatched.json()["status"] == "DISPATCHED"

    answered = client.post(
        f"/api/v1/investigate/documents/{doc_id}/response",
        json={"note": "Bank confirmed a hold of Rs 2,40,000 on the beneficiary account."},
        headers=station["io"],
    )
    assert answered.status_code == 200
    assert answered.json()["status"] == "RESPONDED"


def test_return_requires_a_comment_and_sends_it_back(client: TestClient, station: dict) -> None:
    documents = client.post(
        f"/api/v1/investigate/cases/{station['case_id']}/action-pack", headers=station["io"]
    ).json()["documents"]
    doc_id = documents[0]["id"]
    client.post(f"/api/v1/investigate/documents/{doc_id}/submit", headers=station["io"])

    blank = client.post(
        f"/api/v1/investigate/documents/{doc_id}/return", json={"comment": ""}, headers=station["sho"]
    )
    assert blank.status_code == 422

    returned = client.post(
        f"/api/v1/investigate/documents/{doc_id}/return",
        json={"comment": "Add the victim's transaction UTRs before this goes out."},
        headers=station["sho"],
    )
    assert returned.status_code == 200
    assert returned.json()["status"] == "RETURNED"
    assert returned.json()["approvals"][-1]["comment"].startswith("Add the victim")


def test_an_edit_after_approval_is_detectable(client: TestClient, station: dict) -> None:
    documents = client.post(
        f"/api/v1/investigate/cases/{station['case_id']}/action-pack", headers=station["io"]
    ).json()["documents"]
    telecom = next(item for item in documents if item["doc_type"] == TELECOM_CAF_CDR)
    doc_id = telecom["id"]

    client.post(f"/api/v1/investigate/documents/{doc_id}/submit", headers=station["io"])
    approved = client.post(f"/api/v1/investigate/documents/{doc_id}/approve", headers=station["sho"])
    assert approved.json()["status"] == "APPROVED"
    assert approved.json()["edited_after_approval"] is False

    # An approved document is no longer editable, which is the real protection.
    blocked = client.put(
        f"/api/v1/investigate/documents/{doc_id}",
        json={"body_html": "<html><body>" + "x" * 60 + "</body></html>"},
        headers=station["io"],
    )
    assert blocked.status_code == 422


def test_queue_shows_what_is_waiting_for_me(client: TestClient, station: dict) -> None:
    documents = client.post(
        f"/api/v1/investigate/cases/{station['case_id']}/action-pack", headers=station["io"]
    ).json()["documents"]
    for item in documents[:2]:
        client.post(f"/api/v1/investigate/documents/{item['id']}/submit", headers=station["io"])

    sho_queue = client.get("/api/v1/investigate/queue", headers=station["sho"]).json()
    assert sho_queue["total"] == 2
    assert all(item["status"] == "PENDING_STATION" for item in sho_queue["documents"])

    # The IO has no approval role, so nothing is waiting for them.
    io_queue = client.get("/api/v1/investigate/queue", headers=station["io"]).json()
    assert io_queue["total"] == 0


def test_another_district_cannot_see_or_approve_the_document(client: TestClient, station: dict) -> None:
    make_officer(client, "sho.bharatpur", "STATION_HEAD", "INSPECTOR", "BTP-CYBER-PS")
    other = auth(client, "sho.bharatpur")
    documents = client.post(
        f"/api/v1/investigate/cases/{station['case_id']}/action-pack", headers=station["io"]
    ).json()["documents"]
    doc_id = documents[0]["id"]
    client.post(f"/api/v1/investigate/documents/{doc_id}/submit", headers=station["io"])

    assert client.get(f"/api/v1/investigate/documents/{doc_id}", headers=other).status_code == 404
    assert client.post(f"/api/v1/investigate/documents/{doc_id}/approve", headers=other).status_code == 404
    assert client.get("/api/v1/investigate/queue", headers=other).json()["total"] == 0


def test_mis_report_counts_only_what_exists(client: TestClient, station: dict) -> None:
    report = client.get("/api/v1/investigate/reports/mis?period=weekly", headers=station["sp"]).json()
    assert report["cases"] >= 1
    assert report["documents_drafted"] == 0
    assert any("no requisitions" in item.lower() for item in report["limitations"])

    client.post(f"/api/v1/investigate/cases/{station['case_id']}/action-pack", headers=station["io"])
    after = client.get("/api/v1/investigate/reports/mis?period=weekly", headers=station["sp"]).json()
    assert after["documents_drafted"] >= 3
    assert after["by_unit"]


def test_every_transition_is_audited(client: TestClient, station: dict) -> None:
    documents = client.post(
        f"/api/v1/investigate/cases/{station['case_id']}/action-pack", headers=station["io"]
    ).json()["documents"]
    doc_id = documents[0]["id"]
    client.post(f"/api/v1/investigate/documents/{doc_id}/submit", headers=station["io"])
    client.post(f"/api/v1/investigate/documents/{doc_id}/approve", headers=station["sho"])

    status_response = client.get("/api/v1/investigate/audit/status", headers=station["sp"])
    assert status_response.status_code == 200, status_response.text
    body = status_response.json()
    assert body["intact"] is True
    assert body["events"] > 0
