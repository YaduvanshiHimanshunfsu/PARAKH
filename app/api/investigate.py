from __future__ import annotations

"""Investigation Mode API.

Every route here persists or reads case data and requires an officer account.
Citizen Mode routes live in ``routes.py`` and remain anonymous and ephemeral
(DECISIONS.md ADR-001).
"""

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import HTMLResponse
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.uploads import read_apk_upload
from app.config import Settings, get_settings
from app.core.auth import (
    bearer_scheme,
    issue_token,
    lock_remaining,
    mfa_required,
    register_failure,
    register_success,
    require_officer,
    revoke_token,
    verify_password,
    verify_totp,
)
from app.core.permissions import Permission, can_investigate_it_act, has_permission
from app.services import audit_service


async def _is_visible(session: AsyncSession, case_id: str, user: UserRecord) -> bool:
    return await case_service.get_case(session, case_id, viewer=user) is not None


async def _visible_case_or_404(session: AsyncSession, case_id: str, user: UserRecord):
    """Load a case the user may see, or raise the same 404 as an unknown id."""

    case = await case_service.get_case(session, case_id, viewer=user)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case {case_id} was not found.")
    return case


def require_permission(permission: Permission):
    """Dependency factory: refuse the request unless the role allows it.

    Checked server-side on every mutating endpoint. The console hides what a
    role cannot do, but hiding a button is not access control.
    """

    async def dependency(user: UserRecord = Depends(require_officer)) -> UserRecord:
        if not has_permission(user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Your role ({user.role}) is not permitted to {permission.value.replace('.', ' ')}.",
            )
        return user

    return dependency
from app.db.models import UnitRecord, UserRecord
from app.db.session import get_session
from app.schemas import (
    AuditChainStatus,
    AuditEntry,
    AuditTrailResponse,
    CaseAssignRequest,
    CaseTransferRequest,
    ArtifactType,
    CampaignGraph,
    CaseDetail,
    CaseSearchResponse,
    CaseSource,
    CaseStatus,
    CaseStatusUpdate,
    DashboardSummary,
    HeatListEntry,
    IdentifierType,
    InvestigateSubmitRequest,
    LinkedCase,
    LoginRequest,
    LoginResponse,
    PreCheckRequest,
    PreCheckResponse,
    RiskLevel,
    SimilarCase,
    UserRole,
    WebsiteAnalyzeRequest,
)
from app.services import campaign_service, case_service, dashboard_service, link_service, report_builder
from app.services.apk_analyzer import ApkAnalyzer, ApkParsingError
from app.services.artifact_analyzer import ArtifactAnalyzer
from app.services.scam_analyzer import ProviderUnavailableError
from app.services.url_enrichment import UrlEnrichmentService
from app.services.website_analyzer import WebsiteAnalyzer, WebsiteFetchError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/investigate", tags=["Investigation"])


def get_artifact_analyzer(request: Request) -> ArtifactAnalyzer:
    return request.app.state.artifact_analyzer


def get_apk_analyzer(request: Request) -> ApkAnalyzer:
    return request.app.state.apk_analyzer


def get_website_analyzer(request: Request) -> WebsiteAnalyzer:
    return request.app.state.website_analyzer


async def enforce_rate_limit(request: Request) -> None:
    await request.app.state.rate_limiter.check(request)


# --- authentication --------------------------------------------------------


@router.post("/auth/login", response_model=LoginResponse, summary="Sign in as an officer")
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    user = (
        await session.execute(select(UserRecord).where(UserRecord.username == payload.username))
    ).scalar_one_or_none()

    # One generic failure message for unknown user, wrong password, locked and
    # disabled account, so the response cannot be used to enumerate usernames
    # or to discover that an account exists and is locked.
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password."
    )

    if user is not None and lock_remaining(user):
        await audit_service.append_event(
            session,
            action=audit_service.Action.LOGIN_FAILED,
            actor=user,
            target_type="user",
            target_id=str(user.id),
            details={"reason": "locked"},
        )
        await session.commit()
        logger.warning("login_locked username_length=%d", len(payload.username))
        raise invalid

    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        if user is not None:
            locked_for = register_failure(
                user,
                threshold=settings.login_lockout_threshold,
                minutes=settings.login_lockout_minutes,
                max_minutes=settings.login_lockout_max_minutes,
            )
            await audit_service.append_event(
                session,
                action=audit_service.Action.LOGIN_FAILED,
                actor=user,
                target_type="user",
                target_id=str(user.id),
                details={"failed_logins": user.failed_logins, "locked_minutes": locked_for},
            )
            # Raising below aborts the request transaction, so the counter and
            # the audit entry must be committed now or the lockout never
            # takes effect and the attempt leaves no trace.
            await session.commit()
        logger.warning("login_failed username_length=%d", len(payload.username))
        raise invalid

    if mfa_required(user.role, settings.mfa_required_roles) and user.totp_secret:
        if not payload.totp_code or not verify_totp(user.totp_secret, payload.totp_code):
            register_failure(
                user,
                threshold=settings.login_lockout_threshold,
                minutes=settings.login_lockout_minutes,
                max_minutes=settings.login_lockout_max_minutes,
            )
            await audit_service.append_event(
                session,
                action=audit_service.Action.LOGIN_FAILED,
                actor=user,
                target_type="user",
                target_id=str(user.id),
                details={"reason": "totp"},
            )
            await session.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="A valid authenticator code is required for this account.",
            )

    register_success(user)
    token, expires_at = await issue_token(session, user, settings.auth_token_ttl_hours)
    await audit_service.append_event(
        session,
        action=audit_service.Action.LOGIN,
        actor=user,
        target_type="user",
        target_id=str(user.id),
        details={"role": user.role, "rank": user.rank},
    )
    logger.info("login_success username=%s role=%s", user.username, user.role)
    return LoginResponse(
        token=token,
        username=user.username,
        role=UserRole(user.role),
        expires_at=expires_at.isoformat(),
    )


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Revoke the current token")
async def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
    _: UserRecord = Depends(require_officer),
) -> None:
    if credentials is not None:
        await revoke_token(session, credentials.credentials)


@router.get("/me", summary="Current officer identity")
async def me(user: UserRecord = Depends(require_officer)) -> dict:
    return {"username": user.username, "role": user.role}


# --- submission ------------------------------------------------------------


@router.post(
    "/submit",
    response_model=CaseDetail,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_rate_limit)],
    summary="Analyse an artifact and open a case",
)
async def submit_artifact(
    payload: InvestigateSubmitRequest,
    analyzer: ArtifactAnalyzer = Depends(get_artifact_analyzer),
    session: AsyncSession = Depends(get_session),
    user: UserRecord = Depends(require_officer),
) -> CaseDetail:
    """Analyse a message, URL, or email and persist it as a searchable case."""

    try:
        bundle = await analyzer.analyze(
            payload.artifact_type,
            payload.content,
            language=payload.language,
            session=session,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ProviderUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analysis is temporarily unavailable. Please try again shortly.",
        ) from exc

    case = await case_service.create_case(
        session,
        bundle,
        source=payload.source,
        reporter_note=payload.reporter_note,
        user=user,
    )
    return case_service.to_detail(case)


@router.post(
    "/apk/analyze",
    response_model=CaseDetail,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_rate_limit)],
    summary="Statically analyse an Android APK and open a case",
)
async def analyze_apk(
    apk: UploadFile = File(..., description="Android package (.apk)"),
    reporter_note: str | None = Form(default=None),
    source: CaseSource = Form(default=CaseSource.OFFICER),
    settings: Settings = Depends(get_settings),
    analyzer: ApkAnalyzer = Depends(get_apk_analyzer),
    session: AsyncSession = Depends(get_session),
    user: UserRecord = Depends(require_officer),
) -> CaseDetail:
    """Static inspection only — the package is never installed or executed.

    This route is exempt from the global request-size middleware and enforces
    its own ceiling while streaming (DECISIONS.md ADR-004).
    """

    data = await read_apk_upload(apk, settings.max_apk_upload_bytes)
    try:
        bundle = await run_in_threadpool(analyzer.analyze, data, apk.filename)
    except ApkParsingError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    # Blacklist matching applies to APK identifiers exactly as it does to a
    # message, so a known-bad package or C2 host is flagged the same way.
    matches = await UrlEnrichmentService.match_blacklist(session, bundle.identifiers)
    if matches:
        bundle.findings.extend(matches)
        bundle.risk_score = min(100, max(bundle.risk_score, 80))
        bundle.risk_level = RiskLevel.HIGH

    case = await case_service.create_case(
        session, bundle, source=source, reporter_note=reporter_note, user=user
    )
    logger.info(
        "apk_case_created case_id=%s package=%s risk=%s",
        case.case_id,
        bundle.details.get("package"),
        bundle.risk_level,
    )
    return case_service.to_detail(case)


@router.post(
    "/website/analyze",
    response_model=CaseDetail,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_rate_limit)],
    summary="Fetch and analyse a suspicious website, then open a case",
)
async def analyze_website(
    payload: WebsiteAnalyzeRequest,
    analyzer: WebsiteAnalyzer = Depends(get_website_analyzer),
    session: AsyncSession = Depends(get_session),
    user: UserRecord = Depends(require_officer),
) -> CaseDetail:
    """Fetch the page under SSRF and size guards, then score its content.

    Fetching is a deliberate officer action — it is never triggered implicitly
    by citizen-facing analysis (DECISIONS.md ADR-002).
    """

    try:
        bundle = await analyzer.analyze(payload.url)
    except WebsiteFetchError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    matches = await UrlEnrichmentService.match_blacklist(session, bundle.identifiers)
    if matches:
        bundle.findings.extend(matches)
        bundle.risk_score = min(100, max(bundle.risk_score, 80))
        bundle.risk_level = RiskLevel.HIGH

    case = await case_service.create_case(
        session, bundle, source=payload.source, reporter_note=payload.reporter_note, user=user
    )
    logger.info(
        "website_case_created case_id=%s risk=%s", case.case_id, bundle.risk_level
    )
    return case_service.to_detail(case)


# --- linking, similarity, heat-list (Phase 5) ------------------------------


@router.get(
    "/campaigns",
    response_model=CampaignGraph,
    summary="Group linked cases into campaigns, with a graph and variant timeline",
)
async def campaigns(
    max_cases: int = Query(default=1_000, ge=10, le=2_000),
    min_cases: int = Query(default=2, ge=2, le=50),
    session: AsyncSession = Depends(get_session),
    user: UserRecord = Depends(require_officer),
) -> CampaignGraph:
    return await campaign_service.build_campaign_graph(
        session, max_cases=max_cases, min_cases=min_cases
    )


@router.get(
    "/cases/{case_id}/linked",
    response_model=list[LinkedCase],
    summary="Cases sharing an identifier with this one",
)
async def get_linked_cases(
    case_id: str,
    limit: int = Query(default=25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    user: UserRecord = Depends(require_officer),
) -> list[LinkedCase]:
    await _visible_case_or_404(session, case_id, user)
    linked = await link_service.linked_cases(session, case_id, limit=limit)
    return [item for item in linked if await _is_visible(session, item.case.case_id, user)]


@router.get(
    "/cases/{case_id}/similar",
    response_model=list[SimilarCase],
    summary="Repeat-content and near-duplicate matches for this case",
)
async def get_similar_cases(
    case_id: str,
    limit: int = Query(default=25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    user: UserRecord = Depends(require_officer),
) -> list[SimilarCase]:
    await _visible_case_or_404(session, case_id, user)
    similar = await link_service.similar_cases(session, case_id, limit=limit)
    return [item for item in similar if await _is_visible(session, item.case.case_id, user)]


@router.get(
    "/identifiers/{identifier_type}/cases",
    response_model=CaseSearchResponse,
    summary="Every case containing a specific identifier",
)
async def get_identifier_cases(
    identifier_type: IdentifierType,
    value: str = Query(..., min_length=1, max_length=512),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    _: UserRecord = Depends(require_officer),
) -> CaseSearchResponse:
    cases = await link_service.cases_for_identifier(
        session, identifier_type, value, limit=limit
    )
    return CaseSearchResponse(total=len(cases), limit=limit, offset=0, cases=cases)


@router.get(
    "/heatlist",
    response_model=list[HeatListEntry],
    summary="Most frequently reported identifiers",
)
async def get_heatlist(
    identifier_type: IdentifierType | None = Query(default=None, alias="type"),
    days: int | None = Query(default=None, ge=1, le=365),
    limit: int = Query(default=25, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    _: UserRecord = Depends(require_officer),
) -> list[HeatListEntry]:
    return await link_service.heat_list(
        session, identifier_type=identifier_type, days=days, limit=limit
    )


# --- reports and export (Phase 6.5) ----------------------------------------


@router.get(
    "/cases/{case_id}/report",
    response_class=HTMLResponse,
    summary="Printable investigation report for one case",
)
async def case_report(
    case_id: str,
    redacted: bool = Query(default=False, description="Mask identifiers for external sharing"),
    session: AsyncSession = Depends(get_session),
    user: UserRecord = Depends(require_officer),
) -> HTMLResponse:
    """Full evidentiary report, or a masked copy for sharing outside the case."""

    case = await case_service.get_case(session, case_id, viewer=user)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")

    detail = case_service.to_detail(case)
    linked = await link_service.linked_cases(session, case_id, limit=15)
    markup = report_builder.build_case_html(detail, redacted=redacted, linked=linked)
    logger.info(
        "report_generated case_id=%s redacted=%s by=%s", case_id, redacted, user.username
    )
    return HTMLResponse(content=markup)


@router.get(
    "/cases/{case_id}/report.json",
    summary="Structured export of one case",
)
async def case_report_json(
    case_id: str,
    redacted: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
    user: UserRecord = Depends(require_officer),
) -> Response:
    case = await case_service.get_case(session, case_id, viewer=user)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")

    payload = report_builder.build_case_json(case_service.to_detail(case), redacted=redacted)
    return Response(
        content=report_builder.as_json_bytes(payload),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{case_id}.json"'},
    )


@router.get("/export/cases.csv", summary="Bulk export of the filtered case list")
async def export_cases_csv(
    q: str | None = Query(default=None, max_length=200),
    artifact_type: ArtifactType | None = Query(default=None),
    risk_level: RiskLevel | None = Query(default=None),
    case_status: CaseStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=1_000, ge=1, le=5_000),
    session: AsyncSession = Depends(get_session),
    _: UserRecord = Depends(require_officer),
) -> Response:
    rows = await case_service.search_case_records(
        session, query=q, artifact_type=artifact_type, risk_level=risk_level,
        status=case_status, limit=limit,
    )
    return Response(
        content=report_builder.build_cases_csv(rows),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="parakh-cases.csv"'},
    )


@router.get("/export/identifiers.csv", summary="Every identifier across the filtered cases")
async def export_identifiers_csv(
    q: str | None = Query(default=None, max_length=200),
    artifact_type: ArtifactType | None = Query(default=None),
    risk_level: RiskLevel | None = Query(default=None),
    case_status: CaseStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=1_000, ge=1, le=5_000),
    session: AsyncSession = Depends(get_session),
    _: UserRecord = Depends(require_officer),
) -> Response:
    rows = await case_service.search_case_records(
        session, query=q, artifact_type=artifact_type, risk_level=risk_level,
        status=case_status, limit=limit,
    )
    return Response(
        content=report_builder.build_identifiers_csv(rows),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="parakh-identifiers.csv"'},
    )


# --- case retrieval --------------------------------------------------------


@router.get("/cases", response_model=CaseSearchResponse, summary="Search case history")
async def search_cases(
    q: str | None = Query(default=None, max_length=200, description="Free text across content, summary, case ID, and identifiers"),
    artifact_type: ArtifactType | None = Query(default=None),
    risk_level: RiskLevel | None = Query(default=None),
    case_status: CaseStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=25, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    mine: bool = Query(default=False, description="Only cases this officer submitted"),
    session: AsyncSession = Depends(get_session),
    user: UserRecord = Depends(require_officer),
) -> CaseSearchResponse:
    return await case_service.search_cases(
        session,
        viewer=user,
        query=q,
        artifact_type=artifact_type,
        risk_level=risk_level,
        status=case_status,
        limit=limit,
        offset=offset,
        created_by=user.id if mine else None,
    )


@router.get("/dashboard/summary", response_model=DashboardSummary, summary="Dashboard KPIs and trends")
async def dashboard_summary(
    days: int = Query(default=30, ge=1, le=90),
    session: AsyncSession = Depends(get_session),
    _: UserRecord = Depends(require_officer),
) -> DashboardSummary:
    """Every number on the officer dashboard, computed from the case store."""

    return await dashboard_service.build_summary(session, days=days)


@router.get("/cases/{case_id}", response_model=CaseDetail, summary="Full case detail")
async def get_case(
    case_id: str,
    session: AsyncSession = Depends(get_session),
    user: UserRecord = Depends(require_officer),
) -> CaseDetail:
    case = await case_service.get_case(session, case_id, viewer=user)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    return case_service.to_detail(case)


@router.patch("/cases/{case_id}", response_model=CaseDetail, summary="Update case status or notes")
async def update_case(
    case_id: str,
    payload: CaseStatusUpdate,
    session: AsyncSession = Depends(get_session),
    user: UserRecord = Depends(require_officer),
) -> CaseDetail:
    case = await case_service.update_case(session, case_id, payload)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    logger.info("case_updated case_id=%s by=%s", case_id, user.username)
    return case_service.to_detail(case)


# --- C.3 business rules: assignment, transfer, verification ----------------


@router.post(
    "/cases/{case_id}/assign",
    response_model=CaseDetail,
    summary="Assign a case to an officer",
)
async def assign_case(
    case_id: str,
    payload: CaseAssignRequest,
    session: AsyncSession = Depends(get_session),
    user: UserRecord = Depends(require_permission(Permission.CASE_ASSIGN)),
) -> CaseDetail:
    """Assign a case, enforcing the IT Act s.78 rank rule.

    An offence under the IT Act must be investigated by an officer not below
    the rank of Inspector, so assigning such a case to an SI is refused with
    that reason rather than silently accepted.
    """

    case = await _visible_case_or_404(session, case_id, user)
    assignee = (
        await session.execute(
            select(UserRecord).where(UserRecord.username == payload.assignee_username)
        )
    ).scalar_one_or_none()
    if assignee is None or not assignee.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active officer named {payload.assignee_username}.",
        )

    offence_act = payload.offence_act.value if payload.offence_act else case.offence_act
    if offence_act in {"IT_ACT", "BOTH"} and not can_investigate_it_act(assignee.rank):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "IT Act 2000 section 78 requires an officer not below the rank of Inspector to "
                f"investigate this offence. {assignee.username} holds the rank "
                f"{assignee.rank or 'unknown'}."
            ),
        )

    previous = case.assigned_to
    case.assigned_to = assignee.id
    case.offence_act = offence_act
    await audit_service.append_event(
        session,
        action=audit_service.Action.CASE_ASSIGN,
        actor=user,
        target_type="case",
        target_id=case.case_id,
        details={
            "assignee": assignee.username,
            "assignee_rank": assignee.rank,
            "previous_assignee_id": previous,
            "offence_act": offence_act,
            "reason": payload.reason,
        },
    )
    await session.flush()
    await session.refresh(case, attribute_names=["findings", "identifiers"])
    return case_service.to_detail(case)


@router.post(
    "/cases/{case_id}/transfer",
    response_model=CaseDetail,
    summary="Transfer a case to another unit",
)
async def transfer_case(
    case_id: str,
    payload: CaseTransferRequest,
    session: AsyncSession = Depends(get_session),
    user: UserRecord = Depends(require_permission(Permission.CASE_TRANSFER)),
) -> CaseDetail:
    """Move a case to another unit. The reason is mandatory and audited."""

    case = await _visible_case_or_404(session, case_id, user)
    unit = (
        await session.execute(select(UnitRecord).where(UnitRecord.code == payload.unit_code))
    ).scalar_one_or_none()
    if unit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No unit with code {payload.unit_code}."
        )

    before = {"unit_id": case.unit_id, "unit_path": case.unit_path}
    case.unit_id = unit.id
    case.unit_path = unit.path
    # The previous assignee belongs to the old unit, so the case arrives
    # unassigned rather than owned by someone who can no longer see it.
    case.assigned_to = None
    await audit_service.append_event(
        session,
        action=audit_service.Action.CASE_TRANSFER,
        actor=user,
        target_type="case",
        target_id=case.case_id,
        details={"from": before, "to": {"unit_id": unit.id, "unit_path": unit.path}, "reason": payload.reason},
    )
    await session.flush()
    await session.refresh(case, attribute_names=["findings", "identifiers"])
    return case_service.to_detail(case)


@router.post(
    "/cases/{case_id}/verify",
    response_model=CaseDetail,
    summary="Confirm a citizen report so it counts as intelligence",
)
async def verify_case(
    case_id: str,
    session: AsyncSession = Depends(get_session),
    user: UserRecord = Depends(require_permission(Permission.CASE_VERIFY)),
) -> CaseDetail:
    """Release a citizen report from quarantine.

    Until an officer confirms it, a citizen report does not feed the heat-list
    or the "already seen in police cases" check, because anyone can submit one.
    """

    case = await _visible_case_or_404(session, case_id, user)
    case.verified = True
    await audit_service.append_event(
        session,
        action=audit_service.Action.CASE_VERIFY,
        actor=user,
        target_type="case",
        target_id=case.case_id,
        details={"source": case.source},
    )
    await session.flush()
    await session.refresh(case, attribute_names=["findings", "identifiers"])
    return case_service.to_detail(case)


@router.get(
    "/cases/{case_id}/audit",
    response_model=AuditTrailResponse,
    summary="Who did what to this case, with chain verification",
)
async def case_audit_trail(
    case_id: str,
    session: AsyncSession = Depends(get_session),
    user: UserRecord = Depends(require_officer),
) -> AuditTrailResponse:
    await _visible_case_or_404(session, case_id, user)
    events = await audit_service.events_for_target(session, "case", case_id)
    status_ = await audit_service.verify_stored_chain(session)
    return AuditTrailResponse(
        status=AuditChainStatus(
            intact=status_.intact,
            events=status_.events,
            broken_at=status_.broken_at,
            summary=status_.summary,
        ),
        entries=[
            AuditEntry(
                seq=event.seq,
                at=event.at.isoformat(),
                actor_name=event.actor_name,
                actor_role=event.actor_role,
                action=event.action,
                target_type=event.target_type,
                target_id=event.target_id,
                details=event.details or {},
            )
            for event in events
        ],
    )


@router.get(
    "/audit/status",
    response_model=AuditChainStatus,
    summary="Verify the whole audit chain",
)
async def audit_status(
    session: AsyncSession = Depends(get_session),
    user: UserRecord = Depends(require_permission(Permission.AUDIT_VIEW)),
) -> AuditChainStatus:
    status_ = await audit_service.verify_stored_chain(session)
    return AuditChainStatus(
        intact=status_.intact,
        events=status_.events,
        broken_at=status_.broken_at,
        summary=status_.summary,
    )
