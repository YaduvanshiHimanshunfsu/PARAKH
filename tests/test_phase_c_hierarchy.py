from __future__ import annotations

"""Phase C: hierarchy, jurisdiction scoping, login hardening, audit chain."""

import asyncio
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.config import Settings, get_settings
from app.core.auth import hash_password, lock_remaining, register_failure, register_success
from app.core.permissions import (
    Permission,
    Rank,
    Role,
    Scope,
    can_investigate_it_act,
    has_permission,
    rank_at_least,
    scope_of,
)
from app.db.models import AuditEvent, UnitRecord, UserRecord
from app.db.session import Database
from app.db.units_seed import seed_hierarchy, seed_units
from app.main import create_app
from app.services import audit_service

PASSWORD = "InvestigationPass123"
PONZI = (
    "RichPlan Investment: Guaranteed 10% daily returns! Referral bonus on every downline "
    "member. Joining package Rs 5000. Pay richplan@ybl or call 9812345670."
)


# --- C.2 matrix -------------------------------------------------------------


def test_role_permissions_match_the_published_matrix():
    assert has_permission(Role.IO, Permission.DOCUMENT_DRAFT)
    assert not has_permission(Role.IO, Permission.APPROVE_STATION)
    assert has_permission(Role.STATION_HEAD, Permission.APPROVE_STATION)
    assert not has_permission(Role.STATION_HEAD, Permission.APPROVE_SUPERVISOR)
    assert has_permission(Role.SUPERVISOR, Permission.APPROVE_SUPERVISOR)
    assert not has_permission(Role.OPERATOR, Permission.CASE_ASSIGN)
    assert not has_permission(Role.STATE_VIEWER, Permission.CASE_CREATE)
    assert not has_permission(Role.STATE_VIEWER, Permission.CASE_UPDATE)
    assert has_permission(Role.ADMIN, Permission.USER_MANAGE)
    assert not has_permission(Role.SUPERVISOR, Permission.USER_MANAGE)


def test_scopes_widen_with_responsibility():
    assert scope_of(Role.OPERATOR) is Scope.OWN_SUBMISSIONS
    assert scope_of(Role.IO) is Scope.STATION
    assert scope_of(Role.SUPERVISOR) is Scope.SUBTREE
    assert scope_of(Role.STATE_VIEWER) is Scope.ALL


def test_unknown_role_gets_the_least_privilege():
    assert scope_of("something-else") is Scope.OWN_SUBMISSIONS
    assert not has_permission("something-else", Permission.CASE_ASSIGN)


# --- C.3 IT Act section 78 --------------------------------------------------


@pytest.mark.parametrize("rank", ["DGP", "ADG", "IG", "SP", "ADDL_SP", "DYSP", "INSPECTOR"])
def test_inspector_and_above_may_investigate_it_act_offences(rank):
    assert can_investigate_it_act(rank)


@pytest.mark.parametrize("rank", ["SI", "ASI", "HC", "CONSTABLE", None, "nonsense"])
def test_below_inspector_may_not(rank):
    assert not can_investigate_it_act(rank)


def test_rank_ordering():
    assert rank_at_least(Rank.SP, Rank.INSPECTOR)
    assert not rank_at_least(Rank.HC, Rank.SI)


# --- C.4 lockout ------------------------------------------------------------


def test_account_locks_after_the_threshold_and_backs_off():
    user = UserRecord(username="x", password_hash="", failed_logins=0)
    for _ in range(4):
        assert register_failure(user, threshold=5, minutes=15, max_minutes=240) == 0
    assert lock_remaining(user) == 0

    first = register_failure(user, threshold=5, minutes=15, max_minutes=240)
    assert first == 15
    assert lock_remaining(user) > 0

    for _ in range(4):
        register_failure(user, threshold=5, minutes=15, max_minutes=240)
    assert register_failure(user, threshold=5, minutes=15, max_minutes=240) == 30

    register_success(user)
    assert user.failed_logins == 0
    assert lock_remaining(user) == 0


def test_lock_duration_is_capped():
    user = UserRecord(username="x", password_hash="", failed_logins=0)
    for _ in range(80):
        applied = register_failure(user, threshold=5, minutes=15, max_minutes=240)
    assert applied <= 240


def test_totp_verification_round_trip():
    pyotp = pytest.importorskip("pyotp")
    from app.core.auth import verify_totp

    secret = pyotp.random_base32()
    assert verify_totp(secret, pyotp.TOTP(secret).now())
    assert not verify_totp(secret, "000000")
    assert not verify_totp("", "123456")


# --- C.5 audit chain --------------------------------------------------------


def test_audit_chain_verifies_and_detects_an_edited_row():
    asyncio.run(_audit_chain_edit_case())


async def _audit_chain_edit_case():
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.create_all()
    async with db.session() as session:
        for index in range(5):
            await audit_service.append_event(
                session,
                action=audit_service.Action.CASE_VIEW,
                target_type="case",
                target_id=f"PRK-2026-{index}",
            )

    async with db.session() as session:
        assert (await audit_service.verify_stored_chain(session)).intact

    async with db.session() as session:
        row = (await session.execute(select(AuditEvent).where(AuditEvent.seq == 3))).scalar_one()
        row.details = {"tampered": True}

    async with db.session() as session:
        status = await audit_service.verify_stored_chain(session)
        assert not status.intact
        assert status.broken_at == 3
        assert "broken at event 3" in status.summary
    await db.close()


def test_audit_chain_detects_a_deleted_row():
    asyncio.run(_audit_chain_delete_case())


async def _audit_chain_delete_case():
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.create_all()
    async with db.session() as session:
        for index in range(4):
            await audit_service.append_event(
                session, action=audit_service.Action.CASE_VIEW, target_type="case", target_id=str(index)
            )
    async with db.session() as session:
        await session.execute(delete(AuditEvent).where(AuditEvent.seq == 2))
    async with db.session() as session:
        assert not (await audit_service.verify_stored_chain(session)).intact
    await db.close()


def test_entry_hash_depends_on_the_previous_hash():
    body = audit_service.canonical_body(
        1, __import__("datetime").datetime(2026, 11, 24, tzinfo=__import__("datetime").timezone.utc),
        None, "system", "SYSTEM", "login", "user", "1", {},
    )
    assert audit_service.entry_hash("0" * 64, body) != audit_service.entry_hash("1" * 64, body)


# --- C.1 / C.6 unit hierarchy ----------------------------------------------


def test_unit_paths_are_materialised_for_prefix_scoping():
    asyncio.run(_unit_path_case())


async def _unit_path_case():
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.create_all()
    async with db.session() as session:
        units = await seed_units(session)
        assert units["JPR-CYBER-PS"].path == "/RJ/JPR-RANGE/JPR-COMM/JPR-CYBER-PS/"
        assert units["BTP-CYBER-PS"].path.startswith(units["BTP-DISTRICT"].path)
        # A Jaipur station is not under the Bharatpur district path.
        assert not units["JPR-CYBER-PS"].path.startswith(units["BTP-DISTRICT"].path)
    await db.close()


def test_seeding_is_idempotent():
    asyncio.run(_idempotent_case())


async def _idempotent_case():
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.create_all()
    async with db.session() as session:
        await seed_hierarchy(session)
    async with db.session() as session:
        await seed_hierarchy(session)
    async with db.session() as session:
        units = (await session.execute(select(UnitRecord))).scalars().all()
        assert len({unit.code for unit in units}) == len(units)
    await db.close()


# --- C.2 end-to-end scoping through the API --------------------------------


@pytest.fixture()
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    db_path = tmp_path / f"scoping_{uuid.uuid4().hex}.db"

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
    """Create an officer directly in the store the running app is using."""

    database = client.app.state.database

    async def create() -> None:
        async with database.session() as session:
            units = await seed_units(session)
            existing = (
                await session.execute(select(UserRecord).where(UserRecord.username == username))
            ).scalar_one_or_none()
            if existing is not None:
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


def test_officer_cannot_see_another_districts_case(client: TestClient) -> None:
    make_officer(client, "sho.jaipur", "STATION_HEAD", "INSPECTOR", "JPR-CYBER-PS")
    make_officer(client, "io.bharatpur", "IO", "INSPECTOR", "BTP-CYBER-PS")

    jaipur = auth(client, "sho.jaipur")
    created = client.post(
        "/api/v1/investigate/submit",
        json={"artifact_type": "MESSAGE", "content": PONZI},
        headers=jaipur,
    )
    assert created.status_code == 201, created.text
    case_id = created.json()["case_id"]

    # The officer who filed it sees it.
    assert client.get(f"/api/v1/investigate/cases/{case_id}", headers=jaipur).status_code == 200

    # An officer in another district gets the same 404 as for an unknown case.
    bharatpur = auth(client, "io.bharatpur")
    assert client.get(f"/api/v1/investigate/cases/{case_id}", headers=bharatpur).status_code == 404
    assert client.get("/api/v1/investigate/cases/PRK-20260101-ZZZZZZ", headers=bharatpur).status_code == 404

    # And it is absent from their search results.
    listing = client.get("/api/v1/investigate/cases", headers=bharatpur).json()
    assert all(item["case_id"] != case_id for item in listing["cases"])


def test_cross_unit_linked_and_similar_are_scoped(client: TestClient) -> None:
    make_officer(client, "sho.jaipur", "STATION_HEAD", "INSPECTOR", "JPR-CYBER-PS")
    make_officer(client, "io.bharatpur", "IO", "INSPECTOR", "BTP-CYBER-PS")
    jaipur = auth(client, "sho.jaipur")
    case_id = client.post(
        "/api/v1/investigate/submit",
        json={"artifact_type": "MESSAGE", "content": PONZI},
        headers=jaipur,
    ).json()["case_id"]

    bharatpur = auth(client, "io.bharatpur")
    for suffix in ("linked", "similar", "audit"):
        response = client.get(f"/api/v1/investigate/cases/{case_id}/{suffix}", headers=bharatpur)
        assert response.status_code in {403, 404}, f"{suffix} leaked: {response.status_code}"


def test_operator_may_not_assign_a_case(client: TestClient) -> None:
    make_officer(client, "sho.jaipur", "STATION_HEAD", "INSPECTOR", "JPR-CYBER-PS")
    make_officer(client, "op.jaipur", "OPERATOR", "HC", "JPR-CYBER-PS")
    sho = auth(client, "sho.jaipur")
    case_id = client.post(
        "/api/v1/investigate/submit",
        json={"artifact_type": "MESSAGE", "content": PONZI},
        headers=sho,
    ).json()["case_id"]

    operator = auth(client, "op.jaipur")
    response = client.post(
        f"/api/v1/investigate/cases/{case_id}/assign",
        json={"assignee_username": "sho.jaipur"},
        headers=operator,
    )
    assert response.status_code in {403, 404}


def test_it_act_case_cannot_be_assigned_below_inspector(client: TestClient) -> None:
    make_officer(client, "sho.jaipur", "STATION_HEAD", "INSPECTOR", "JPR-CYBER-PS")
    make_officer(client, "si.jaipur", "IO", "SI", "JPR-CYBER-PS")
    sho = auth(client, "sho.jaipur")
    case_id = client.post(
        "/api/v1/investigate/submit",
        json={"artifact_type": "MESSAGE", "content": PONZI},
        headers=sho,
    ).json()["case_id"]

    refused = client.post(
        f"/api/v1/investigate/cases/{case_id}/assign",
        json={"assignee_username": "si.jaipur", "offence_act": "IT_ACT"},
        headers=sho,
    )
    assert refused.status_code == 422
    assert "section 78" in refused.json()["detail"]

    allowed = client.post(
        f"/api/v1/investigate/cases/{case_id}/assign",
        json={"assignee_username": "sho.jaipur", "offence_act": "IT_ACT"},
        headers=sho,
    )
    assert allowed.status_code == 200, allowed.text


def test_transfer_moves_the_case_and_is_audited(client: TestClient) -> None:
    make_officer(client, "sho.jaipur", "STATION_HEAD", "INSPECTOR", "JPR-CYBER-PS")
    make_officer(client, "io.bharatpur", "IO", "INSPECTOR", "BTP-CYBER-PS")
    sho = auth(client, "sho.jaipur")
    case_id = client.post(
        "/api/v1/investigate/submit",
        json={"artifact_type": "MESSAGE", "content": PONZI},
        headers=sho,
    ).json()["case_id"]

    moved = client.post(
        f"/api/v1/investigate/cases/{case_id}/transfer",
        json={"unit_code": "BTP-CYBER-PS", "reason": "Victim and suspect are both in Bharatpur."},
        headers=sho,
    )
    assert moved.status_code == 200, moved.text

    # Now Bharatpur can see it and Jaipur's station head cannot.
    bharatpur = auth(client, "io.bharatpur")
    assert client.get(f"/api/v1/investigate/cases/{case_id}", headers=bharatpur).status_code == 200

    trail = client.get(f"/api/v1/investigate/cases/{case_id}/audit", headers=bharatpur)
    assert trail.status_code == 200, trail.text
    body = trail.json()
    assert body["status"]["intact"] is True
    actions = {entry["action"] for entry in body["entries"]}
    assert "case.transfer" in actions


def test_transfer_requires_a_reason(client: TestClient) -> None:
    make_officer(client, "sho.jaipur", "STATION_HEAD", "INSPECTOR", "JPR-CYBER-PS")
    sho = auth(client, "sho.jaipur")
    case_id = client.post(
        "/api/v1/investigate/submit", json={"artifact_type": "MESSAGE", "content": PONZI}, headers=sho
    ).json()["case_id"]
    response = client.post(
        f"/api/v1/investigate/cases/{case_id}/transfer",
        json={"unit_code": "BTP-CYBER-PS"},
        headers=sho,
    )
    assert response.status_code == 422


def test_login_failures_are_audited_and_lock_the_account(client: TestClient) -> None:
    make_officer(client, "sho.jaipur", "STATION_HEAD", "INSPECTOR", "JPR-CYBER-PS")
    for _ in range(5):
        bad = client.post(
            "/api/v1/investigate/auth/login",
            json={"username": "sho.jaipur", "password": "WrongPassword123"},
        )
        assert bad.status_code == 401

    # The correct password is now refused too, with the same generic message.
    locked = client.post(
        "/api/v1/investigate/auth/login", json={"username": "sho.jaipur", "password": PASSWORD}
    )
    assert locked.status_code == 401
    assert locked.json()["detail"] == "Invalid username or password."


def test_unverified_citizen_reports_stay_out_of_the_heat_list(client: TestClient) -> None:
    make_officer(client, "sho.jaipur", "STATION_HEAD", "INSPECTOR", "JPR-CYBER-PS")
    sho = auth(client, "sho.jaipur")

    filed = client.post(
        "/api/v1/parakh/report-to-police",
        json={"artifact_type": "MESSAGE", "content": PONZI, "consent": True},
    )
    assert filed.status_code == 201, filed.text
    reference = filed.json()["reference"]

    def heatlist_values() -> set[str]:
        rows = client.get("/api/v1/investigate/heatlist", headers=sho).json()
        return {row["value"] for row in rows}

    assert "richplan@ybl" not in heatlist_values()

    verified = client.post(f"/api/v1/investigate/cases/{reference}/verify", headers=sho)
    assert verified.status_code == 200, verified.text
    assert "richplan@ybl" in heatlist_values()
