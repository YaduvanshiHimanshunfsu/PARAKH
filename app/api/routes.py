from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status

from app.config import Settings, get_settings
from app.schemas import (
    AnalyzeRequest,
    AnalysisResponse,
    EmailAnalyzeRequest,
    EmailAnalysisResponse,
    HealthResponse,
    MediaKind,
    MediaExtractionResponse,
    MediaValidationResponse,
    RescuePlan,
    RescueRequest,
    SafeNextStepRequest,
    SafeNextStepResponse,
    QrAnalyzeRequest,
    QrAnalyzeResponse,
    OrganisationVerifyRequest,
    OrganisationVerifyResponse,
    TrustedChannel,
    SimpleExplainRequest,
    SimpleExplainResponse,
    ArtifactType,
    CaseSource,
    CitizenReportRequest,
    CitizenReportResponse,
    PreCheckRequest,
    PreCheckResponse as SafePreCheckResponse,
    RiskLevel,
    UrlAnalysis,
    UrlAnalyzeRequest,
    UrlRiskLevel,
)
from app.services import case_service, link_service
from app.services.artifact_analyzer import ArtifactAnalyzer
from app.services.email_analyzer import EmailAnalyzer
from app.services.scam_analyzer import ProviderUnavailableError, ScamAnalyzer
from app.services.media_validation import MediaValidationError, MediaValidator
from app.services.media_analyzer import MediaAnalyzer, MediaExtractionUnavailableError
from app.services.rescue_planner import RescuePlanner
from app.services.decision_checker import DecisionChecker
from app.services.organisation_verifier import OrganisationVerifier
from app.services.qr_analyzer import QrAnalyzer
from app.services.simple_explainer import SimpleExplainer
from app.services.trusted_channel_service import TrustedChannelService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["PARAKH"])


def get_analyzer(request: Request) -> ScamAnalyzer:
    return request.app.state.analyzer


def get_email_analyzer(request: Request) -> EmailAnalyzer:
    return request.app.state.email_analyzer


def get_rescue_planner(request: Request) -> RescuePlanner:
    return request.app.state.rescue_planner


def get_media_analyzer(request: Request) -> MediaAnalyzer:
    return request.app.state.media_analyzer


def get_decision_checker(request: Request) -> DecisionChecker:
    return request.app.state.decision_checker


def get_qr_analyzer(request: Request) -> QrAnalyzer:
    return request.app.state.qr_analyzer


def get_organisation_verifier(request: Request) -> OrganisationVerifier:
    return request.app.state.organisation_verifier


def get_trusted_channel_service(request: Request) -> TrustedChannelService:
    return request.app.state.trusted_channel_service


def get_simple_explainer(request: Request) -> SimpleExplainer:
    return request.app.state.simple_explainer


def get_artifact_analyzer_public(request: Request) -> ArtifactAnalyzer:
    """Shared with Investigation Mode; reached here only via explicit consent."""

    return request.app.state.artifact_analyzer


async def enforce_rate_limit(request: Request) -> None:
    await request.app.state.rate_limiter.check(request)


@router.get("/health", response_model=HealthResponse, include_in_schema=False)
async def health(request: Request, settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Operational status only â€” never configuration values or secrets.

    Reports per-subsystem availability so a demo problem is diagnosable at a
    glance. Every analyser except live AI works without its dependency, so a
    degraded subsystem is reported rather than failing the whole check.
    """

    database_ready = False
    case_count: int | None = None
    database = getattr(request.app.state, "database", None)
    if database is not None:
        try:
            from sqlalchemy import func, select

            from app.db.models import CaseRecord

            async with database.session() as session:
                case_count = (await session.execute(select(func.count(CaseRecord.id)))).scalar_one()
            database_ready = True
        except Exception as exc:
            logger.warning("health_database_unavailable error=%s", type(exc).__name__)

    return HealthResponse(
        status="ok",
        provider_configured=settings.provider_is_configured,
        offline_fallback_enabled=settings.enable_offline_fallback,
        investigation_store_ready=database_ready,
        case_count=case_count,
        apk_analysis_available=_apk_analysis_available(),
        website_analysis_available=True,
        domain_age_enabled=settings.domain_age_enabled,
    )


def _apk_analysis_available() -> bool:
    """APK analysis degrades without pyaxmlparser; surface that before a demo."""

    import importlib.util

    return importlib.util.find_spec("pyaxmlparser") is not None


@router.post(
    "/parakh/analyze",
    response_model=AnalysisResponse,
    dependencies=[Depends(enforce_rate_limit)],
    summary="Analyse suspicious message text for Indian scam patterns",
)
async def analyze_scam(
    payload: AnalyzeRequest,
    analyzer: ScamAnalyzer = Depends(get_analyzer),
) -> AnalysisResponse:
    try:
        return await analyzer.analyze(payload)
    except ProviderUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Live scam analysis is unavailable. Please try again shortly.",
        ) from exc


@router.post(
    "/parakh/url/analyze",
    response_model=UrlAnalysis,
    dependencies=[Depends(enforce_rate_limit)],
    summary="Inspect a URL for phishing signals, TLS status, and optional reputation matches",
)
async def analyze_url(
    payload: UrlAnalyzeRequest,
    analyzer: ScamAnalyzer = Depends(get_analyzer),
) -> UrlAnalysis:
    return await analyzer.analyze_url(payload.url)


@router.post(
    "/parakh/email/analyze",
    response_model=EmailAnalysisResponse,
    dependencies=[Depends(enforce_rate_limit)],
    summary="Analyse a pasted email or raw .eml for phishing, authentication evidence, and unsafe links",
)
async def analyze_email(
    payload: EmailAnalyzeRequest,
    analyzer: EmailAnalyzer = Depends(get_email_analyzer),
) -> EmailAnalysisResponse:
    try:
        return await analyzer.analyze(payload)
    except ProviderUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Live email analysis is unavailable. Please try again shortly.",
        ) from exc


@router.post(
    "/parakh/media/validate",
    response_model=MediaValidationResponse,
    dependencies=[Depends(enforce_rate_limit)],
    summary="Validate an opt-in screenshot or voice upload without retaining it",
)
async def validate_media(
    media: UploadFile = File(...),
    media_kind: MediaKind = Form(...),
    consent: bool = Form(False),
    settings: Settings = Depends(get_settings),
) -> MediaValidationResponse:
    """Establish a safe upload boundary before media extraction is introduced.

    This endpoint does not analyse, save, log, or return the file. It only
    verifies its declared type, binary structure, dimensions/size, and consent.
    """

    if not consent:
        await media.close()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Consent is required before media can be processed.",
        )

    try:
        validated = await MediaValidator(settings).validate(media, media_kind)
    except MediaValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    finally:
        await media.close()

    return MediaValidationResponse(
        media_kind=validated.media_kind,
        mime_type=validated.mime_type,
        size_bytes=validated.size_bytes,
        consent_acknowledged=True,
        retention_notice="The upload was validated in memory and was not saved or analysed.",
    )


@router.post(
    "/parakh/media/extract",
    response_model=MediaExtractionResponse,
    dependencies=[Depends(enforce_rate_limit)],
    summary="Extract reviewable text from a consented screenshot or voice note",
)
async def extract_media(
    media: UploadFile = File(...),
    media_kind: MediaKind = Form(...),
    consent: bool = Form(False),
    settings: Settings = Depends(get_settings),
    analyzer: MediaAnalyzer = Depends(get_media_analyzer),
) -> MediaExtractionResponse:
    """Extract text in memory only; no transcript is invented if extraction fails."""

    if not consent:
        await media.close()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Consent is required before media can be processed.",
        )

    try:
        validated = await MediaValidator(settings).validate(media, media_kind)
        return await analyzer.extract(validated)
    except MediaValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except MediaExtractionUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="We could not read this media. Please paste or type the message text to continue.",
        ) from exc
    finally:
        await media.close()


@router.post(
    "/parakh/rescue-plan",
    response_model=RescuePlan,
    dependencies=[Depends(enforce_rate_limit)],
    summary="Give deterministic next steps after a potential scam exposure",
)
async def create_rescue_plan(
    payload: RescueRequest,
    planner: RescuePlanner = Depends(get_rescue_planner),
) -> RescuePlan:
    """Return reviewed safety guidance; no secret or account data is accepted."""

    return planner.create_plan(payload)


@router.post(
    "/parakh/safe-next-step",
    response_model=SafeNextStepResponse,
    dependencies=[Depends(enforce_rate_limit)],
    summary="Return deterministic advice before a risky next action",
)
async def safe_next_step(
    payload: SafeNextStepRequest,
    checker: DecisionChecker = Depends(get_decision_checker),
) -> SafeNextStepResponse:
    return checker.check(payload)


@router.post(
    "/parakh/qr/analyze",
    response_model=QrAnalyzeResponse,
    dependencies=[Depends(enforce_rate_limit)],
    summary="Assess a browser-decoded QR payload without uploading the QR image",
)
async def analyze_qr(
    payload: QrAnalyzeRequest,
    analyzer: QrAnalyzer = Depends(get_qr_analyzer),
) -> QrAnalyzeResponse:
    return await analyzer.analyze(payload)


@router.post(
    "/parakh/organisation/verify",
    response_model=OrganisationVerifyResponse,
    dependencies=[Depends(enforce_rate_limit)],
    summary="Find claimed organisations and independent official verification routes",
)
async def verify_organisation(
    payload: OrganisationVerifyRequest,
    verifier: OrganisationVerifier = Depends(get_organisation_verifier),
) -> OrganisationVerifyResponse:
    return verifier.verify(payload)


@router.get(
    "/parakh/trusted-channels",
    response_model=list[TrustedChannel],
    dependencies=[Depends(enforce_rate_limit)],
    summary="List official reporting and recovery channels without collecting secrets",
)
async def trusted_channels(service: TrustedChannelService = Depends(get_trusted_channel_service)) -> list[TrustedChannel]:
    return service.list_channels()


@router.post(
    "/parakh/explain-simply",
    response_model=SimpleExplainResponse,
    dependencies=[Depends(enforce_rate_limit)],
    summary="Explain a verdict in deterministic plain English, Hindi, and Hinglish",
)
async def explain_simply(
    payload: SimpleExplainRequest,
    explainer: SimpleExplainer = Depends(get_simple_explainer),
) -> SimpleExplainResponse:
    return explainer.explain(payload)


@router.post(
    "/parakh/report-to-police",
    response_model=CitizenReportResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_rate_limit)],
    summary="Forward an analysed item to the police queue, with explicit consent",
)
async def report_to_police(
    payload: CitizenReportRequest,
    request: Request,
    analyzer: ArtifactAnalyzer = Depends(get_artifact_analyzer_public),
) -> CitizenReportResponse:
    """The only path by which Citizen Mode may write to the case store.

    Consent is explicit and required: without ``consent=true`` nothing is
    stored and the request is rejected. This preserves the ADR-001 guarantee
    that ordinary citizen analysis leaves no trace.
    """

    if not payload.consent:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Explicit consent is required before an item is sent to the police queue.",
        )

    database = getattr(request.app.state, "database", None)
    if database is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Reporting is not available on this deployment.",
        )

    try:
        async with database.session() as session:
            bundle = await analyzer.analyze(
                payload.artifact_type, payload.content, language=payload.language, session=session
            )
            case = await case_service.create_case(
                session,
                bundle,
                source=CaseSource.CITIZEN,
                reporter_note=payload.reporter_note,
                user=None,
            )
            reference = case.case_id
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ProviderUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Reporting is temporarily unavailable. Please try again shortly.",
        ) from exc

    logger.info("citizen_report_filed case_id=%s type=%s", reference, payload.artifact_type.value)
    return CitizenReportResponse(
        reference=reference,
        message=(
            "Your report has been added to the review queue. Keep this reference. "
            "For money already lost, call 1930 immediately â€” this tool does not replace that."
        ),
        helpline="1930",
        official_portal="https://cybercrime.gov.in/",
    )


@router.post(
    "/parakh/check-before-open",
    response_model=SafePreCheckResponse,
    dependencies=[Depends(enforce_rate_limit)],
    summary="Fast warning about a link before the user opens it",
)
async def check_before_open(
    payload: PreCheckRequest,
    request: Request,
    analyzer: ScamAnalyzer = Depends(get_analyzer),
) -> SafePreCheckResponse:
    """Warn a user before they open a risky link.

    PS01 asks the system to "warn users before they open a risky link", so this
    is kept deliberately cheap: deterministic URL structure checks plus an
    indexed lookup of prior reports. No page is fetched and no AI is called,
    which keeps it fast enough for a browser extension or bot to call inline.
    """

    analysis = await analyzer.analyze_url(payload.url)
    reasons = [signal.explanation for signal in analysis.signals[:4]]

    reported = 0
    database = getattr(request.app.state, "database", None)
    if database is not None:
        try:
            async with database.session() as session:
                reported, prior_reasons = await link_service.precheck_url(session, payload.url)
                reasons = prior_reasons + reasons
        except Exception as exc:
            # A reporting-history lookup must never block the safety answer.
            logger.warning("precheck_history_unavailable error=%s", type(exc).__name__)

    risk = _precheck_risk(analysis.risk_level, reported)
    return SafePreCheckResponse(
        url=payload.url,
        risk_level=risk,
        should_warn=risk is not RiskLevel.LOW,
        reasons=reasons[:6],
        previously_reported=reported,
    )


def _precheck_risk(url_risk: UrlRiskLevel, reported: int) -> RiskLevel:
    if url_risk in {UrlRiskLevel.CRITICAL, UrlRiskLevel.HIGH} or reported >= 3:
        return RiskLevel.HIGH
    if url_risk is UrlRiskLevel.MEDIUM or reported >= 1:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


@router.post(
    "/scamshield/analyze",
    response_model=AnalysisResponse,
    dependencies=[Depends(enforce_rate_limit)],
    deprecated=True,
    include_in_schema=False,
)
async def analyze_scam_legacy(
    payload: AnalyzeRequest,
    analyzer: ScamAnalyzer = Depends(get_analyzer),
) -> AnalysisResponse:
    """Temporary compatibility alias; migrate clients to /parakh/analyze."""

    return await analyze_scam(payload, analyzer)


