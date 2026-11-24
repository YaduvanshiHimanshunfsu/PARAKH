from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables only."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "staging", "production"] = "development"
    api_v1_prefix: str = "/api/v1"
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    gemini_api_key: SecretStr | None = None
    # Enabled models differ by account, region, tier, and API lifecycle. This
    # ordered allow-list is resolved against models visible to the supplied key.
    gemini_model_preferences: str = (
        "gemini-3.6-flash,gemini-3.5-flash,gemini-3.5-flash-lite,"
        "gemini-2.5-flash,gemini-flash-latest"
    )
    gemini_max_model_attempts: int = 3
    gemini_timeout_seconds: float = 20.0

    # Optional URL reputation providers. A user-submitted URL is sent to a
    # provider only when its corresponding key is configured.
    web_risk_api_key: SecretStr | None = None
    virustotal_api_key: SecretStr | None = None
    url_intelligence_enabled: bool = True
    url_tls_probe_enabled: bool = True
    url_analysis_timeout_seconds: float = 5.0
    # How the website fetcher identifies itself. Scam sites target phones
    # and cloak or block desktop crawlers, so a mobile profile sees the page
    # a victim would see. Announcing ourselves as PARAKH told the operator we
    # were looking (defect D10).
    website_fetch_profile: str = "mobile"
    # Optional separate egress for a pilot deployment. Off by default: the
    # demo must not depend on an external proxy.
    website_fetch_proxy: str | None = None
    max_urls_per_message: int = 3

    enable_offline_fallback: bool = True
    rate_limit_requests: int = 20
    rate_limit_window_seconds: int = 60
    daily_anonymous_limit: int = Field(default=120, ge=10, le=2_000)
    upstash_redis_rest_url: SecretStr | None = None
    upstash_redis_rest_token: SecretStr | None = None
    rate_limit_backend_timeout_seconds: float = Field(default=2.0, ge=0.2, le=10.0)
    rate_limit_fail_open: bool = False
    trust_proxy_headers: bool = True
    provider_max_concurrent_requests: int = Field(default=4, ge=1, le=32)
    provider_queue_wait_seconds: float = Field(default=3.0, ge=0.1, le=15.0)
    sentry_dsn: SecretStr | None = None
    sentry_traces_sample_rate: float = Field(default=0.05, ge=0, le=1)

    # Keep application requests comfortably below the 4.5 MB serverless payload
    # limit. This includes multipart boundaries as well as the media itself.
    max_request_bytes: int = Field(default=3_250_000, ge=1_024, le=4_000_000)
    media_upload_enabled: bool = True
    max_image_upload_bytes: int = Field(default=3_000_000, ge=1_024, le=3_500_000)
    max_audio_upload_bytes: int = Field(default=3_000_000, ge=1_024, le=3_500_000)
    max_image_pixels: int = Field(default=20_000_000, ge=1, le=25_000_000)
    allowed_image_mime_types: str = "image/jpeg,image/png,image/webp"
    allowed_audio_mime_types: str = "audio/mpeg,audio/wav,audio/webm,audio/mp4,audio/x-m4a"

    # Raw .eml uploads are accepted as text JSON. Attachments are never accepted
    # separately or opened; the larger limit only preserves header evidence.
    email_dkim_verification_enabled: bool = True
    email_dns_timeout_seconds: float = 4.0

    # --- PS01 investigation layer (DECISIONS.md ADR-001, ADR-003, ADR-004) ---
    # Citizen Mode never writes here. Investigation Mode persists cases so they
    # can be searched, linked, and exported for police investigation.
    database_url: str = "sqlite+aiosqlite:///./parakh_cases.db"
    db_echo: bool = False

    # Officer bootstrap. A single seeded account is created at startup when both
    # values are set; there is deliberately no self-registration.
    officer_username: str | None = None
    officer_password: SecretStr | None = None
    auth_token_ttl_hours: int = Field(default=12, ge=1, le=720)

    # APKs exceed the global request ceiling, so the APK route carries its own
    # limit rather than widening the limit on every text endpoint (ADR-004).
    max_apk_upload_bytes: int = Field(default=60_000_000, ge=1_000_000, le=200_000_000)

    # Domain-age lookups use RDAP over HTTPS (JSON, no WHOIS parsing).
    domain_age_enabled: bool = True
    domain_age_timeout_seconds: float = Field(default=4.0, ge=0.5, le=20.0)
    domain_intel_cache_hours: int = Field(default=168, ge=1, le=8_760)

    # Redirect chains are resolved hop-by-hop with the SSRF guard re-applied at
    # every hop. Never set this high; each hop is a separate network request.
    redirect_following_enabled: bool = True
    max_redirect_hops: int = Field(default=5, ge=1, le=10)

    @field_validator("allowed_origins")
    @classmethod
    def validate_origins(cls, value: str) -> str:
        origins = [origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()]
        if not origins:
            raise ValueError("ALLOWED_ORIGINS must contain at least one origin")
        if "*" in origins:
            raise ValueError("Wildcard CORS origins are not allowed")
        return ",".join(origins)

    @property
    def cors_origins(self) -> list[str]:
        return self.allowed_origins.split(",")

    @property
    def provider_is_configured(self) -> bool:
        return bool(self.gemini_api_key and self.gemini_api_key.get_secret_value())

    @property
    def gemini_model_candidates(self) -> tuple[str, ...]:
        """Return a de-duplicated, explicit list of models safe to attempt."""

        seen: set[str] = set()
        candidates: list[str] = []
        for raw_name in self.gemini_model_preferences.split(","):
            name = raw_name.strip().removeprefix("models/")
            if name and name not in seen:
                candidates.append(name)
                seen.add(name)
        return tuple(candidates)

    @staticmethod
    def _csv_values(value: str) -> tuple[str, ...]:
        return tuple(item.strip().lower() for item in value.split(",") if item.strip())

    @property
    def image_mime_types(self) -> tuple[str, ...]:
        return self._csv_values(self.allowed_image_mime_types)

    @property
    def audio_mime_types(self) -> tuple[str, ...]:
        return self._csv_values(self.allowed_audio_mime_types)


@lru_cache
def get_settings() -> Settings:
    return Settings()

