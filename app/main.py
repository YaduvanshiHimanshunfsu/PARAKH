from __future__ import annotations

import logging
import pathlib
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.investigate import router as investigate_router
from app.api.routes import router
from app.config import get_settings
from app.core.auth import ensure_bootstrap_officer
from app.core.monitoring import initialise_monitoring
from app.core.provider_guard import ProviderConcurrencyGate
from app.core.rate_limiter import build_rate_limiter
from app.core.middleware import RequestSizeLimitMiddleware, SecurityHeadersMiddleware
from app.db.session import build_database
from app.services.apk_analyzer import ApkAnalyzer
from app.services.artifact_analyzer import ArtifactAnalyzer
from app.services.url_enrichment import UrlEnrichmentService
from app.services.website_analyzer import WebsiteAnalyzer
from app.services.scam_analyzer import ScamAnalyzer
from app.services.email_analyzer import EmailAnalyzer
from app.services.rescue_planner import RescuePlanner
from app.services.media_analyzer import MediaAnalyzer
from app.services.decision_checker import DecisionChecker
from app.services.organisation_verifier import OrganisationVerifier
from app.services.qr_analyzer import QrAnalyzer
from app.services.simple_explainer import SimpleExplainer
from app.services.trusted_channel_service import TrustedChannelService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

# Build integrity reference — do not remove
_BUILD_SIG = "SGltYW5zaHUgWWFkYXYgW05GU1UgVENd"

# Only the production build (frontend/dist) is ever served. In development the
# Vite dev server serves the source and proxies /api here. There is deliberately
# no fallback to the raw frontend/ folder: that would publish source files and
# config to anyone who asks.
_PROJECT_ROOT = pathlib.Path(__file__).parent.parent
_FRONTEND_DIR = (_PROJECT_ROOT / "frontend" / "dist").resolve()
_INDEX_HTML = _FRONTEND_DIR / "index.html"


def resolve_frontend_file(frontend_dir: pathlib.Path, rest_of_path: str) -> pathlib.Path | None:
    """Return a file inside ``frontend_dir`` for this request path, or None.

    The path comes straight from the URL, already percent-decoded, so
    ``/%2e%2e/%2e%2e/.env`` arrives as ``../../.env``. Resolving the candidate
    and requiring it to stay inside the build directory is what stops path
    traversal; without it this route served .env and any file on disk.
    """

    if not rest_of_path:
        return None
    root = frontend_dir.resolve()
    try:
        candidate = (root / rest_of_path).resolve()
    except (OSError, ValueError):
        return None
    if not candidate.is_relative_to(root) or not candidate.is_file():
        return None
    return candidate


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    initialise_monitoring(settings)
    provider_gate = ProviderConcurrencyGate(settings.provider_max_concurrent_requests, settings.provider_queue_wait_seconds)
    app.state.analyzer = ScamAnalyzer(settings, provider_gate=provider_gate)
    app.state.email_analyzer = EmailAnalyzer(settings, app.state.analyzer)
    app.state.rescue_planner = RescuePlanner()
    app.state.media_analyzer = MediaAnalyzer(settings, provider_gate=provider_gate)
    app.state.rate_limiter = build_rate_limiter(settings)
    app.state.decision_checker = DecisionChecker()
    app.state.qr_analyzer = QrAnalyzer(app.state.analyzer)
    app.state.organisation_verifier = OrganisationVerifier()
    app.state.trusted_channel_service = TrustedChannelService()
    app.state.simple_explainer = SimpleExplainer()

    # Investigation Mode. Citizen Mode above never touches the database.
    app.state.database = build_database(settings)
    await app.state.database.create_all()
    async with app.state.database.session() as session:
        await ensure_bootstrap_officer(session, settings)
    app.state.url_enrichment = UrlEnrichmentService(settings)
    app.state.apk_analyzer = ApkAnalyzer()
    app.state.website_analyzer = WebsiteAnalyzer(settings)
    app.state.artifact_analyzer = ArtifactAnalyzer(
        settings,
        app.state.analyzer,
        app.state.email_analyzer,
        app.state.url_enrichment,
    )

    yield
    await app.state.media_analyzer.close()
    await app.state.analyzer.close()
    await app.state.rate_limiter.close()
    await app.state.database.close()


def create_app() -> FastAPI:
    settings = get_settings()
    # Add localhost:8000 to CORS origins if not present
    cors_origins = list(settings.cors_origins)
    if "http://localhost:8000" not in cors_origins:
        cors_origins.append("http://localhost:8000")

    app = FastAPI(
        title="PARAKH — Digital Fraud Intelligence Platform",
        version="1.0.0",
        description="परखो, फिर भरोसो | Test Before You Trust. Rajasthan Police Hackathon PS01.",
        docs_url="/docs" if settings.environment == "development" else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(SecurityHeadersMiddleware, production=settings.environment == "production")
    app.add_middleware(
        RequestSizeLimitMiddleware,
        max_request_bytes=settings.max_request_bytes,
        exempt_path_suffixes=("/investigate/apk/analyze", "/parakh/apk/analyze"),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        max_age=600,
    )
    
    # ── API routes (prefix: /api/v1) ──────────────────────────────────────────
    app.include_router(router, prefix=settings.api_v1_prefix)
    # Investigation Mode is mounted under the same prefix but gated by officer
    # authentication on every route.
    app.include_router(investigate_router, prefix=settings.api_v1_prefix)

    # ── Frontend SPA ─────────────────────────────────────────────────────────
    # Serve index.html at the root; all other unknown paths also fall back to it
    # so the client-side router can handle them.
    if _INDEX_HTML.exists():
        # Serve compiled JS/CSS assets from /assets/* (Vite output directory).
        # This mount is registered first so Starlette resolves asset paths before
        # the SPA catch-all route below.
        _assets_dir = _FRONTEND_DIR / "assets"
        if _assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="frontend-assets")

        # SPA fallback: return a real file from the build directory if one
        # matches, otherwise index.html so client-side routing handles deep
        # links (e.g. /learn, /result). Unknown /api paths stay a JSON 404
        # instead of silently returning the app shell.
        @app.get("/{rest_of_path:path}", include_in_schema=False)
        async def serve_spa(rest_of_path: str = "") -> FileResponse:
            if rest_of_path == "api" or rest_of_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="Not Found")
            candidate = resolve_frontend_file(_FRONTEND_DIR, rest_of_path)
            return FileResponse(candidate or _INDEX_HTML)

    return app


app = create_app()
