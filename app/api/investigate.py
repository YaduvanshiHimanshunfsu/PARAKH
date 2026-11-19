from __future__ import annotations

"""Investigation Mode API.

Every route here persists or reads case data and requires an officer account.
Citizen Mode routes live in ``routes.py`` and remain anonymous and ephemeral
(DECISIONS.md ADR-001).
"""

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.auth import (
    bearer_scheme,
    issue_token,
    require_officer,
    revoke_token,
    verify_password,
)
from app.db.models import UserRecord
from app.db.session import get_session
from app.schemas import (
    ArtifactType,
    CaseDetail,
    CaseSearchResponse,
    CaseSource,
    CaseStatus,
    CaseStatusUpdate,
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
from app.services import case_service, link_service, report_builder
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

    # One generic failure message for unknown user, wrong password, and disabled
    # account, so the response cannot be used to enumerate valid usernames.
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        logger.warning("login_failed username_length=%d", len(payload.username))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    token, expires_at = await issue_token(session, user, settings.auth_token_ttl_hours)
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
    """Static inspection only â€” the package is never installed or executed.

    This route is exempt from the global request-size middleware and enforces
    its own ceiling while streaming (DECISIONS.md ADR-004).
    """

    limit = settings.max_apk_upload_bytes
    chunks: list[bytes] = []
    total = 0
    try:
        while chunk := await apk.read(1_048_576):
            total += len(chunk)
            if total > limit:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"The APK exceeds the {limit // 1_000_000} MB upload limit.",
                )
            chunks.append(chunk)
    finally:
        await apk.close()

    if total == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="The uploaded file is empty."
        )

    try:
        bundle = analyzer.analyze(b"".join(chunks), filename=apk.filename)
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

    Fetching is a deliberate officer action â€” it is never triggered implicitly
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
    "/cases/{case_id}/linked",
    response_model=list[LinkedCase],
    summary="Cases sharing an identifier with this one",
)
async def get_linked_cases(
    case_id: str,
    limit: int = Query(default=25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _: UserRecord = Depends(require_officer),
) -> list[LinkedCase]:
    return await link_service.linked_cases(session, case_id, limit=limit)


@router.get(
    "/cases/{case_id}/similar",
    response_model=list[SimilarCase],
    summary="Repeat-content and near-duplicate matches for this case",
)
async def get_similar_cases(
    case_id: str,
    limit: int = Query(default=25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    _: UserRecord = Depends(require_officer),
) -> list[SimilarCase]:
    return await link_service.similar_cases(session, case_id, limit=limit)


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

    case = await case_service.get_case(session, case_id)
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
    _: UserRecord = Depends(require_officer),
) -> Response:
    case = await case_service.get_case(session, case_id)
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
    session: AsyncSession = Depends(get_session),
    _: UserRecord = Depends(require_officer),
) -> CaseSearchResponse:
    return await case_service.search_cases(
        session,
        query=q,
        artifact_type=artifact_type,
        risk_level=risk_level,
        status=case_status,
        limit=limit,
        offset=offset,
    )


@router.get("/cases/{case_id}", response_model=CaseDetail, summary="Full case detail")
async def get_case(
    case_id: str,
    session: AsyncSession = Depends(get_session),
    _: UserRecord = Depends(require_officer),
) -> CaseDetail:
    case = await case_service.get_case(session, case_id)
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

