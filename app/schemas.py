from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Verdict(str, Enum):
    SCAM = "SCAM"
    SUSPICIOUS = "SUSPICIOUS"
    SAFE = "SAFE"


class Severity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AnalysisSource(str, Enum):
    AI = "AI"
    # The reviewed rule engine alone (AI not configured or unavailable).
    RULE_FALLBACK = "RULE_FALLBACK"
    # AI verdict fused with the rule engine (planversionalpha.md B.9).
    AI_RULES = "AI+RULES"


class MediaKind(str, Enum):
    SCREENSHOT = "SCREENSHOT"
    VOICE_NOTE = "VOICE_NOTE"


class ExposureState(str, Enum):
    RECEIVED_ONLY = "RECEIVED_ONLY"
    CLICKED_LINK = "CLICKED_LINK"
    SHARED_PERSONAL_INFO = "SHARED_PERSONAL_INFO"
    SHARED_SECRET = "SHARED_SECRET"
    INSTALLED_APP_OR_SCREEN_SHARE = "INSTALLED_APP_OR_SCREEN_SHARE"
    SENT_MONEY = "SENT_MONEY"


class RescueUrgency(str, Enum):
    PREVENTIVE = "PREVENTIVE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SafeAction(str, Enum):
    CLICK_LINK = "CLICK_LINK"
    CALL_NUMBER = "CALL_NUMBER"
    PAY_MONEY = "PAY_MONEY"
    INSTALL_APP = "INSTALL_APP"
    SHARE_OTP = "SHARE_OTP"
    SCAN_OR_PAY_QR = "SCAN_OR_PAY_QR"
    OPEN_ATTACHMENT = "OPEN_ATTACHMENT"


class SafetyDecision(str, Enum):
    STOP_NOW = "STOP_NOW"
    VERIFY_FIRST = "VERIFY_FIRST"
    LOWER_RISK_STILL_VERIFY = "LOWER_RISK_STILL_VERIFY"


class QrPayloadKind(str, Enum):
    UPI_PAYMENT = "UPI_PAYMENT"
    URL = "URL"
    TEXT = "TEXT"
    UNKNOWN = "UNKNOWN"


class EvidenceKind(str, Enum):
    MESSAGE = "MESSAGE"
    SCREENSHOT = "SCREENSHOT"
    VOICE_TRANSCRIPT = "VOICE_TRANSCRIPT"
    EMAIL = "EMAIL"
    URL = "URL"
    TRANSACTION_REFERENCE = "TRANSACTION_REFERENCE"


class EmailType(str, Enum):
    PHISHING = "PHISHING"
    IMPERSONATION = "IMPERSONATION"
    BUSINESS_EMAIL_COMPROMISE = "BUSINESS_EMAIL_COMPROMISE"
    MALWARE_DELIVERY = "MALWARE_DELIVERY"
    MARKETING_OR_NEWSLETTER = "MARKETING_OR_NEWSLETTER"
    TRANSACTIONAL = "TRANSACTIONAL"
    PERSONAL_OR_UNKNOWN = "PERSONAL_OR_UNKNOWN"


class AuthenticationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SOFTFAIL = "SOFTFAIL"
    NEUTRAL = "NEUTRAL"
    NONE = "NONE"
    NOT_PRESENT = "NOT_PRESENT"
    NOT_VERIFIABLE = "NOT_VERIFIABLE"
    ERROR = "ERROR"


class UrlRiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class ReputationStatus(str, Enum):
    FLAGGED = "FLAGGED"
    NO_KNOWN_LISTING = "NO_KNOWN_LISTING"
    NOT_CHECKED = "NOT_CHECKED"
    ERROR = "ERROR"


class TlsStatus(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNREACHABLE = "UNREACHABLE"
    NOT_CHECKED = "NOT_CHECKED"


class InputLanguage(str, Enum):
    AUTO = "auto"
    ENGLISH = "en"
    HINDI = "hi"
    HINGLISH = "hinglish"
    BENGALI = "bn"
    TAMIL = "ta"
    TELUGU = "te"
    MARATHI = "mr"
    GUJARATI = "gu"
    PUNJABI = "pa"
    URDU = "ur"
    SPANISH = "es"
    FRENCH = "fr"
    ARABIC = "ar"
    OTHER = "other"


class ScamCategory(str, Enum):
    UPI_FRAUD = "UPI_FRAUD"
    KYC_SCAM = "KYC_SCAM"
    GOVERNMENT_IMPERSONATION = "GOVERNMENT_IMPERSONATION"
    LOTTERY_PRIZE = "LOTTERY_PRIZE"
    FAKE_JOB = "FAKE_JOB"
    INVESTMENT_FRAUD = "INVESTMENT_FRAUD"
    OTP_THEFT = "OTP_THEFT"
    PHISHING_LINK = "PHISHING_LINK"
    COURIER_SCAM = "COURIER_SCAM"
    TECH_SUPPORT = "TECH_SUPPORT"
    ROMANCE_SCAM = "ROMANCE_SCAM"
    # PS01 fraud families: predatory instant-loan apps, Ponzi/MLM referral
    # schemes, illegal betting platforms, and utility-disconnection lures.
    LOAN_APP_FRAUD = "LOAN_APP_FRAUD"
    PONZI_MLM = "PONZI_MLM"
    BETTING_GAMBLING = "BETTING_GAMBLING"
    UTILITY_BILL_SCAM = "UTILITY_BILL_SCAM"
    # Phase B typologies: CBI/ED/customs "digital arrest" extortion, malicious
    # APKs sent by message, sextortion (split from romance), and OLX-style
    # "army officer" buyer/seller fraud.
    DIGITAL_ARREST = "DIGITAL_ARREST"
    MALICIOUS_APP = "MALICIOUS_APP"
    SEXTORTION = "SEXTORTION"
    MARKETPLACE_FRAUD = "MARKETPLACE_FRAUD"
    UNKNOWN = "UNKNOWN"


class PsychologicalTactic(str, Enum):
    FALSE_URGENCY = "FALSE_URGENCY"
    AUTHORITY_IMPERSONATION = "AUTHORITY_IMPERSONATION"
    FEAR_INDUCTION = "FEAR_INDUCTION"
    TOO_GOOD_TO_BE_TRUE = "TOO_GOOD_TO_BE_TRUE"
    OTP_SOCIAL_ENGINEERING = "OTP_SOCIAL_ENGINEERING"
    PROCESSING_FEE_TRAP = "PROCESSING_FEE_TRAP"
    SOCIAL_PROOF_FABRICATION = "SOCIAL_PROOF_FABRICATION"
    RECIPROCITY_TRAP = "RECIPROCITY_TRAP"


class AnalyzeRequest(BaseModel):
    """Untrusted text submitted by the browser for analysis."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    message: str = Field(min_length=3, max_length=5_000)
    language: InputLanguage = InputLanguage.AUTO

    @field_validator("message")
    @classmethod
    def reject_null_bytes(cls, value: str) -> str:
        if "\x00" in value:
            raise ValueError("Message contains an invalid character")
        return value


class RedFlag(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    phrase: str = Field(min_length=1, max_length=160)
    explanation: str = Field(min_length=5, max_length=320)


class UrlSignal(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    code: str = Field(min_length=2, max_length=64)
    severity: Severity
    explanation: str = Field(min_length=5, max_length=320)


class TlsDetails(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: TlsStatus
    issuer: str | None = Field(default=None, max_length=320)
    expires_at: str | None = Field(default=None, max_length=80)
    hostname_verified: bool | None = None


class ReputationProviderResult(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    provider: str = Field(min_length=2, max_length=64)
    status: ReputationStatus
    threat_types: list[str] = Field(default_factory=list, max_length=8)
    malicious_count: int | None = Field(default=None, ge=0)
    suspicious_count: int | None = Field(default=None, ge=0)
    detail: str | None = Field(default=None, max_length=240)


class SiteProfile(BaseModel):
    """Cautious domain-level context; never proof for a specific page or request."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: str = Field(min_length=3, max_length=64)
    name: str | None = Field(default=None, max_length=160)
    description: str = Field(min_length=10, max_length=400)
    verification_note: str = Field(min_length=10, max_length=400)


class UrlAnalysis(BaseModel):
    """A conservative, explainable assessment of one user-supplied URL."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    original_url: str = Field(min_length=1, max_length=2_048)
    normalized_url: str | None = Field(default=None, max_length=2_048)
    host: str | None = Field(default=None, max_length=253)
    registered_domain: str | None = Field(default=None, max_length=253)
    risk_level: UrlRiskLevel
    risk_score: int = Field(ge=0, le=100)
    signals: list[UrlSignal] = Field(default_factory=list, max_length=12)
    tls: TlsDetails
    reputation: list[ReputationProviderResult] = Field(default_factory=list, max_length=3)
    site_profile: SiteProfile | None = None
    summary: str = Field(min_length=5, max_length=500)
    limitations: str = Field(min_length=10, max_length=500)


class UrlAnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    url: str = Field(min_length=4, max_length=2_048)


class EmailAnalyzeRequest(BaseModel):
    """Email input. A raw .eml is strongest because it preserves headers."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    raw_eml: str | None = Field(default=None, max_length=1_000_000)
    sender: str | None = Field(default=None, max_length=512)
    subject: str | None = Field(default=None, max_length=2_000)
    body: str | None = Field(default=None, max_length=100_000)
    language: InputLanguage = InputLanguage.AUTO

    @model_validator(mode="after")
    def requires_email_content(self) -> "EmailAnalyzeRequest":
        if not self.raw_eml and not self.body:
            raise ValueError("Provide a raw .eml file or pasted email body")
        if self.raw_eml and "\x00" in self.raw_eml:
            raise ValueError("Email contains an invalid character")
        return self


class EmailIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    display_name: str | None = Field(default=None, max_length=256)
    address: str | None = Field(default=None, max_length=320)
    domain: str | None = Field(default=None, max_length=253)


class AuthenticationEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    spf: AuthenticationStatus
    dkim: AuthenticationStatus
    dmarc: AuthenticationStatus
    alignment: AuthenticationStatus
    source: str = Field(min_length=3, max_length=120)
    details: list[str] = Field(default_factory=list, max_length=8)


class EmailAttachment(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    filename: str | None = Field(default=None, max_length=512)
    content_type: str = Field(min_length=1, max_length=160)
    size_bytes: int | None = Field(default=None, ge=0)
    risk: UrlRiskLevel
    reason: str = Field(min_length=5, max_length=320)


class EmailAnalysisResponse(BaseModel):
    """Explainable, frontend-safe result for a pasted email or raw .eml."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    verdict: Verdict
    confidence: int = Field(ge=0, le=100)
    severity: Severity
    email_type: EmailType
    scam_category: ScamCategory
    sender: EmailIdentity
    reply_to: EmailIdentity | None = None
    return_path: EmailIdentity | None = None
    authentication: AuthenticationEvidence
    subject: str | None = Field(default=None, max_length=2_000)
    psychological_tactics: list[PsychologicalTactic] = Field(default_factory=list, max_length=6)
    red_flags: list[RedFlag] = Field(default_factory=list, max_length=8)
    action_steps: list[str] = Field(min_length=1, max_length=7)
    hindi_summary: str = Field(min_length=5, max_length=420)
    url_analyses: list[UrlAnalysis] = Field(default_factory=list, max_length=3)
    attachments: list[EmailAttachment] = Field(default_factory=list, max_length=20)
    analysis_source: AnalysisSource
    model_used: str | None = Field(default=None, max_length=120)
    limitations: list[str] = Field(min_length=1, max_length=6)


class RuleEvidence(BaseModel):
    """One reviewed rule that fired, with its log-odds contribution (B.2)."""

    model_config = ConfigDict(extra="forbid")

    rule_id: str = Field(min_length=2, max_length=64)
    phrase: str = Field(min_length=1, max_length=160)
    weight: float
    category: ScamCategory
    counted: bool = True


class AnalysisCore(BaseModel):
    """Fields the AI provider is asked to produce (its response schema).

    ``AnalysisResponse`` adds the rule-engine evidence, which PARAKH always
    computes itself and never asks the model to invent.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    verdict: Verdict
    confidence: int = Field(ge=0, le=100)
    scam_category: ScamCategory
    severity: Severity
    psychological_tactics: list[PsychologicalTactic] = Field(default_factory=list, max_length=6)
    red_flags: list[RedFlag] = Field(default_factory=list, max_length=6)
    action_steps: list[str] = Field(min_length=1, max_length=6)
    hindi_summary: str = Field(min_length=5, max_length=420)
    safe_explanation: str | None = Field(default=None, max_length=420)
    analysis_source: AnalysisSource = AnalysisSource.AI
    model_used: str | None = Field(default=None, max_length=120)
    notice: str | None = Field(default=None, max_length=240)
    url_analyses: list[UrlAnalysis] = Field(default_factory=list, max_length=10)

    @field_validator("action_steps")
    @classmethod
    def action_steps_are_actionable(cls, values: list[str]) -> list[str]:
        clean = [value.strip() for value in values if value and value.strip()]
        if not clean:
            raise ValueError("At least one action step is required")
        return clean

    @model_validator(mode="after")
    def enforce_cautious_safe_results(self) -> "AnalysisCore":
        # A text-only classifier must never present a message as definitively safe.
        if self.verdict == Verdict.SAFE:
            self.severity = Severity.LOW
            self.confidence = min(self.confidence, 75)
            self.safe_explanation = self.safe_explanation or (
                "No obvious scam indicators were found in this text, but verify requests "
                "for money or sensitive information through official channels."
            )
        return self


class AnalysisResponse(AnalysisCore):
    """Strict, frontend-safe contract returned by the API."""

    rule_evidence: list[RuleEvidence] = Field(default_factory=list, max_length=40)
    rule_probability: float | None = Field(default=None, ge=0, le=1)


class MediaValidationResponse(BaseModel):
    """Metadata returned after validating an opt-in media upload.

    The server deliberately does not return the original filename or content.
    Phase 3 will use this validation path before sending approved media to an
    analysis provider.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    media_kind: MediaKind
    mime_type: str = Field(min_length=3, max_length=80)
    size_bytes: int = Field(ge=1)
    consent_acknowledged: bool
    retention_notice: str = Field(min_length=20, max_length=320)


class MediaExtractionCandidate(BaseModel):
    """Strict, provider-produced transcription/OCR output before app metadata is added."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    extracted_text: str = Field(min_length=1, max_length=10_000)
    detected_language: InputLanguage = InputLanguage.AUTO
    limitations: list[str] = Field(min_length=1, max_length=4)


class MediaExtractionResponse(MediaExtractionCandidate):
    """Validated extracted text; uploaded bytes and file names are never returned."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    media_kind: MediaKind


class RescueRequest(BaseModel):
    """A user's stated exposure, paired with an existing analysis outcome."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    exposure_state: ExposureState
    verdict: Verdict
    scam_category: ScamCategory = ScamCategory.UNKNOWN


class RescueAction(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    priority: int = Field(ge=1, le=10)
    instruction: str = Field(min_length=8, max_length=360)
    official_url: str | None = Field(default=None, max_length=2_048)


class RescuePlan(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    urgency: RescueUrgency
    title: str = Field(min_length=5, max_length=160)
    actions: list[RescueAction] = Field(min_length=1, max_length=8)
    evidence_to_preserve: list[str] = Field(default_factory=list, max_length=10)
    limitations: list[str] = Field(min_length=1, max_length=4)


class SafeNextStepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    action: SafeAction
    verdict: Verdict = Verdict.SUSPICIOUS
    scam_category: ScamCategory = ScamCategory.UNKNOWN
    exposure_state: ExposureState = ExposureState.RECEIVED_ONLY


class SafeNextStepResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    decision: SafetyDecision
    title: str = Field(min_length=5, max_length=160)
    simple_explanation: str = Field(min_length=10, max_length=500)
    hindi_explanation: str = Field(min_length=5, max_length=500)
    hinglish_explanation: str = Field(min_length=5, max_length=500)
    steps: list[str] = Field(min_length=1, max_length=5)


class QrAnalyzeRequest(BaseModel):
    """A browser-decoded QR payload. The source image is never sent here."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    payload: str = Field(min_length=1, max_length=2_048)


class QrAnalyzeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    payload_kind: QrPayloadKind
    decision: SafetyDecision
    title: str = Field(min_length=5, max_length=160)
    simple_explanation: str = Field(min_length=10, max_length=500)
    hindi_explanation: str = Field(min_length=5, max_length=500)
    actions: list[str] = Field(min_length=1, max_length=5)
    upi_id: str | None = Field(default=None, max_length=256)
    url_analysis: UrlAnalysis | None = None


class OrganisationVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str = Field(min_length=3, max_length=5_000)


class OrganisationClaim(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    claimed_organisation: str = Field(min_length=2, max_length=160)
    official_domains: list[str] = Field(default_factory=list, max_length=5)
    safe_instruction: str = Field(min_length=10, max_length=500)
    risk_reason: str = Field(min_length=10, max_length=500)


class OrganisationVerifyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    claims: list[OrganisationClaim] = Field(default_factory=list, max_length=8)
    notice: str = Field(min_length=10, max_length=300)


class TrustedChannel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    category: str = Field(min_length=2, max_length=100)
    title: str = Field(min_length=2, max_length=160)
    official_url: str | None = Field(default=None, max_length=2_048)
    phone: str | None = Field(default=None, max_length=32)
    instruction: str = Field(min_length=10, max_length=500)


class SimpleExplainRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    verdict: Verdict
    scam_category: ScamCategory = ScamCategory.UNKNOWN
    red_flags: list[RedFlag] = Field(default_factory=list, max_length=6)
    exposure_state: ExposureState = ExposureState.RECEIVED_ONLY


class SimpleExplainResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    simple_explanation: str = Field(min_length=10, max_length=500)
    hindi_explanation: str = Field(min_length=5, max_length=500)
    hinglish_explanation: str = Field(min_length=5, max_length=500)
    do_steps: list[str] = Field(min_length=1, max_length=3)
    dont_steps: list[str] = Field(min_length=1, max_length=3)
    why_risky: str = Field(min_length=10, max_length=500)


class EvidenceItem(BaseModel):
    """Sanitised evidence metadata suitable for local encrypted storage."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    kind: EvidenceKind
    sha256: str | None = Field(default=None, min_length=64, max_length=64)
    captured_at: str | None = Field(default=None, max_length=40)
    description: str = Field(min_length=3, max_length=500)


class ReportPackDraft(BaseModel):
    """Future local-only report payload; it deliberately has no identity fields."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    case_id: str = Field(min_length=8, max_length=80)
    analysis: AnalysisResponse
    rescue_plan: RescuePlan | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list, max_length=20)
    include_unredacted_evidence: bool = False


class HealthResponse(BaseModel):
    """Operational status. Never contains configuration values or secrets."""

    status: str
    provider_configured: bool
    offline_fallback_enabled: bool
    investigation_store_ready: bool = False
    case_count: int | None = None
    apk_analysis_available: bool = True
    website_analysis_available: bool = True
    domain_age_enabled: bool = True


# ---------------------------------------------------------------------------
# PS01 investigation layer
#
# Citizen Mode keeps every contract above unchanged and persists nothing.
# The types below belong to Investigation Mode, where a submission becomes a
# durable, searchable case. See DECISIONS.md ADR-001.
# ---------------------------------------------------------------------------


class RiskLevel(str, Enum):
    """PS01 asks for Low/Medium/High. Derived from verdict + score in one place."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ArtifactType(str, Enum):
    MESSAGE = "MESSAGE"
    URL = "URL"
    EMAIL = "EMAIL"
    APK = "APK"
    WEBSITE = "WEBSITE"


class IdentifierType(str, Enum):
    """Actionable identifiers PS01 wants extracted and linked across sources."""

    PHONE = "PHONE"
    UPI = "UPI"
    EMAIL = "EMAIL"
    DOMAIN = "DOMAIN"
    URL = "URL"
    IP = "IP"
    IFSC = "IFSC"
    BANK_ACCOUNT = "BANK_ACCOUNT"
    CRYPTO_BTC = "CRYPTO_BTC"
    CRYPTO_ETH = "CRYPTO_ETH"
    TELEGRAM = "TELEGRAM"
    PACKAGE = "PACKAGE"
    CERT_SHA256 = "CERT_SHA256"
    ICON_PHASH = "ICON_PHASH"
    # Phase B.5. TELEGRAM_BOT stores only the bot id; the token itself is kept
    # masked in the evidence and is never used to call the Telegram API.
    TELEGRAM_BOT = "TELEGRAM_BOT"
    CRYPTO_TRON = "CRYPTO_TRON"
    IMEI = "IMEI"
    FIREBASE_DB = "FIREBASE_DB"


class CaseStatus(str, Enum):
    NEW = "NEW"
    UNDER_REVIEW = "UNDER_REVIEW"
    CLOSED = "CLOSED"


class CaseSource(str, Enum):
    CITIZEN = "CITIZEN"
    OFFICER = "OFFICER"


class UserRole(str, Enum):
    CITIZEN = "CITIZEN"
    # OFFICER is the single shared account that existed before Phase C. It is
    # kept so an existing deployment keeps working; new accounts use one of
    # the specific roles below (app/core/permissions.py).
    OFFICER = "OFFICER"
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"
    IO = "IO"
    STATION_HEAD = "STATION_HEAD"
    SUPERVISOR = "SUPERVISOR"
    STATE_VIEWER = "STATE_VIEWER"


class Identifier(BaseModel):
    """One extracted actionable identifier, with the text that surrounded it."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    type: IdentifierType
    value: str = Field(min_length=1, max_length=512)
    raw_value: str = Field(min_length=1, max_length=512)
    context: str | None = Field(default=None, max_length=300)
    confidence: int = Field(default=100, ge=0, le=100)
    # What this identifier is in the case (app/services/identifier_roles.py).
    # Only SUSPECT and UNKNOWN feed linking and the heat-list. Absent on a
    # freshly extracted identifier that has not been stored yet.
    role: str | None = Field(default=None, max_length=20)


class Finding(BaseModel):
    """One triggered indicator. This is what makes a risk score explainable."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    code: str = Field(min_length=2, max_length=64)
    severity: Severity
    explanation: str = Field(min_length=5, max_length=500)
    evidence: str | None = Field(default=None, max_length=500)


class AnalysisBundle(BaseModel):
    """Common shape every analyser emits so one pipeline can persist them all."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    artifact_type: ArtifactType
    risk_level: RiskLevel
    risk_score: int = Field(ge=0, le=100)
    verdict: Verdict | None = None
    summary: str = Field(min_length=5, max_length=1_000)
    findings: list[Finding] = Field(default_factory=list, max_length=60)
    identifiers: list[Identifier] = Field(default_factory=list, max_length=300)
    content_text: str | None = Field(default=None, max_length=200_000)
    content_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    simhash: str | None = Field(default=None, max_length=32)
    details: dict = Field(default_factory=dict)


class InvestigateSubmitRequest(BaseModel):
    """Officer or opted-in citizen submission of a message, URL, or email."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    artifact_type: ArtifactType
    content: str = Field(min_length=3, max_length=100_000)
    language: InputLanguage = InputLanguage.AUTO
    reporter_note: str | None = Field(default=None, max_length=1_000)
    source: CaseSource = CaseSource.OFFICER

    @field_validator("content")
    @classmethod
    def reject_null_bytes(cls, value: str) -> str:
        if "\x00" in value:
            raise ValueError("Content contains an invalid character")
        return value


class CaseSummary(BaseModel):
    """Row shape for the investigation dashboard case list."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    case_id: str = Field(min_length=6, max_length=40)
    artifact_type: ArtifactType
    risk_level: RiskLevel
    risk_score: int = Field(ge=0, le=100)
    status: CaseStatus
    source: CaseSource
    summary: str = Field(min_length=1, max_length=1_000)
    preview: str = Field(default="", max_length=300)
    identifier_count: int = Field(default=0, ge=0)
    finding_count: int = Field(default=0, ge=0)
    created_at: str = Field(max_length=40)


class CaseDetail(CaseSummary):
    """Full case view, including every triggered indicator and identifier."""

    content_text: str | None = Field(default=None, max_length=200_000)
    reporter_note: str | None = Field(default=None, max_length=1_000)
    officer_note: str | None = Field(default=None, max_length=4_000)
    findings: list[Finding] = Field(default_factory=list, max_length=60)
    identifiers: list[Identifier] = Field(default_factory=list, max_length=300)
    details: dict = Field(default_factory=dict)


class CaseSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=200)
    offset: int = Field(ge=0)
    cases: list[CaseSummary] = Field(default_factory=list)


class CaseStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: CaseStatus | None = None
    officer_note: str | None = Field(default=None, max_length=4_000)


class CitizenReportRequest(BaseModel):
    """A citizen forwarding an analysed item to the police queue.

    ``consent`` must be true. Citizen Mode writes nothing without it.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    artifact_type: ArtifactType = ArtifactType.MESSAGE
    content: str = Field(min_length=3, max_length=100_000)
    language: InputLanguage = InputLanguage.AUTO
    reporter_note: str | None = Field(default=None, max_length=1_000)
    consent: bool = False

    @field_validator("content")
    @classmethod
    def reject_null_bytes(cls, value: str) -> str:
        if "\x00" in value:
            raise ValueError("Content contains an invalid character")
        return value


class CitizenReportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reference: str = Field(min_length=6, max_length=40)
    message: str = Field(min_length=10, max_length=500)
    helpline: str = Field(max_length=16)
    official_portal: str = Field(max_length=200)


class LinkedCase(BaseModel):
    """Another case connected to this one by a shared identifier."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    case: CaseSummary
    shared_identifiers: list[str] = Field(default_factory=list, max_length=10)
    link_strength: int = Field(ge=0, le=100)


class SimilarCase(BaseModel):
    """A repeat-content match: the same template, or a reworded variant."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    case: CaseSummary
    match_type: Literal["EXACT_TEMPLATE", "NEAR_DUPLICATE"]
    distance: int = Field(ge=0, le=64)
    similarity: int = Field(ge=0, le=100)


class HeatListEntry(BaseModel):
    """One row of the most-reported identifiers list."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    type: IdentifierType
    value: str = Field(min_length=1, max_length=512)
    case_count: int = Field(ge=0)
    recent_case_count: int = Field(default=0, ge=0)
    # Cases in the 7 days before the recent window, so the UI can show a real
    # week-on-week velocity instead of an invented percentage.
    previous_case_count: int = Field(default=0, ge=0)
    first_seen: str = Field(default="", max_length=40)
    last_seen: str = Field(default="", max_length=40)


class WebsiteAnalyzeRequest(BaseModel):
    """A URL to fetch and analyse. Fetching is never implicit."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    url: str = Field(min_length=4, max_length=2_048)
    reporter_note: str | None = Field(default=None, max_length=1_000)
    source: CaseSource = CaseSource.OFFICER


class PreCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    url: str = Field(min_length=4, max_length=2_048)


class PreCheckResponse(BaseModel):
    """Fast warning used before a user opens a link."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    url: str = Field(max_length=2_048)
    risk_level: RiskLevel
    should_warn: bool
    reasons: list[str] = Field(default_factory=list, max_length=6)
    previously_reported: int = Field(default=0, ge=0)


class ReportedIdentifier(BaseModel):
    """An identifier from the analysed item that already appears in high-risk cases."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    type: IdentifierType
    value: str = Field(min_length=1, max_length=512)
    case_count: int = Field(ge=1)


class CitizenApkAnalysis(BaseModel):
    """Citizen Mode APK result. Analysed in memory; nothing is stored."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    risk_level: RiskLevel
    risk_score: int = Field(ge=0, le=100)
    summary: str = Field(max_length=1_000)
    findings: list[Finding] = Field(default_factory=list, max_length=60)
    identifiers: list[Identifier] = Field(default_factory=list, max_length=300)
    details: dict = Field(default_factory=dict)
    reported_identifiers: list[ReportedIdentifier] = Field(default_factory=list, max_length=20)
    advice: list[str] = Field(default_factory=list, max_length=10)
    helpline: str = Field(default="1930", max_length=20)
    official_portal: str = Field(default="https://cybercrime.gov.in/", max_length=200)


class CampaignIdentifier(BaseModel):
    """An identifier that ties two or more cases of a campaign together."""

    model_config = ConfigDict(extra="forbid")

    type: IdentifierType
    value: str = Field(min_length=1, max_length=512)
    case_count: int = Field(ge=2)


class CampaignTextChange(BaseModel):
    """One wording change between a scam message and its earlier variant."""

    model_config = ConfigDict(extra="forbid")

    before: str = Field(default="", max_length=120)
    after: str = Field(default="", max_length=120)


class CampaignTimelineEntry(BaseModel):
    """One case in a campaign, in the order it was seen."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(max_length=40)
    created_at: str = Field(max_length=40)
    artifact_type: ArtifactType
    risk_level: RiskLevel
    summary: str = Field(default="", max_length=1_000)
    preview: str = Field(default="", max_length=300)
    variant_of: str | None = Field(default=None, max_length=40)
    similarity: int | None = Field(default=None, ge=0, le=100)
    changes: list[CampaignTextChange] = Field(default_factory=list, max_length=8)
    new_identifiers: list[str] = Field(default_factory=list, max_length=8)


class Campaign(BaseModel):
    """A connected group of cases that appear to come from one operation."""

    model_config = ConfigDict(extra="forbid")

    campaign_id: str = Field(max_length=48)
    name: str = Field(max_length=200)
    case_count: int = Field(ge=2)
    risk_level: RiskLevel
    artifact_mix: dict[str, int] = Field(default_factory=dict)
    first_seen: str = Field(default="", max_length=40)
    last_seen: str = Field(default="", max_length=40)
    key_identifiers: list[CampaignIdentifier] = Field(default_factory=list, max_length=12)
    timeline: list[CampaignTimelineEntry] = Field(default_factory=list)


class CampaignNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(max_length=600)
    kind: Literal["case", "identifier"]
    label: str = Field(max_length=200)
    campaign_id: str = Field(max_length=48)
    case_id: str | None = Field(default=None, max_length=40)
    artifact_type: ArtifactType | None = None
    risk_level: RiskLevel | None = None
    identifier_type: IdentifierType | None = None
    value: str | None = Field(default=None, max_length=512)
    case_count: int | None = Field(default=None, ge=0)


class CampaignEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(max_length=600)
    target: str = Field(max_length=600)
    kind: Literal["identifier", "similar"]
    weight: int = Field(ge=0, le=100)


class CampaignGraph(BaseModel):
    """Every campaign found, plus the node-link graph that draws them."""

    model_config = ConfigDict(extra="forbid")

    campaigns: list[Campaign] = Field(default_factory=list)
    nodes: list[CampaignNode] = Field(default_factory=list)
    edges: list[CampaignEdge] = Field(default_factory=list)
    cases_scanned: int = Field(default=0, ge=0)
    linked_case_count: int = Field(default=0, ge=0)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=256)
    # Required only for roles listed in MFA_REQUIRED_ROLES that have enrolled.
    totp_code: str | None = Field(default=None, min_length=6, max_length=8)


class LoginResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    token: str = Field(min_length=20, max_length=200)
    username: str = Field(min_length=3, max_length=64)
    role: UserRole
    expires_at: str = Field(max_length=40)


# --- Phase H.6: endpoints the new frontend needs ------------------------------


class IdentifierCheckRequest(BaseModel):
    """Citizen check of a single UPI ID, phone number, domain or link."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    value: str = Field(min_length=3, max_length=512)


class IdentifierCheckResponse(BaseModel):
    """Whether an identifier appears in verified police cases or the blacklist.

    Counts come only from officer-submitted HIGH-risk cases: anonymous citizen
    reports are not counted until officer verification exists (plan C.4), so
    one person cannot make an innocent UPI ID look "reported".
    """

    model_config = ConfigDict(extra="forbid")

    input: str
    type: IdentifierType | None = None
    value: str | None = None
    risk_level: RiskLevel
    reported_case_count: int = Field(default=0, ge=0)
    blacklisted: bool = False
    blacklist_source: str | None = None
    advice: list[str] = Field(default_factory=list)
    limitations: str


class PublicMeta(BaseModel):
    """Facts about the running engine, so the UI never invents them."""

    model_config = ConfigDict(extra="forbid")

    rule_count: int
    scam_categories: list[str]
    ai_configured: bool
    offline_fallback: bool
    version: str


class ReportStatusResponse(BaseModel):
    """What a citizen may learn about their own report: its stage, nothing else.

    No content, identifiers, risk score or officer note is returned, so a
    guessed reference reveals nothing about another person's report.
    """

    model_config = ConfigDict(extra="forbid")

    reference: str
    status: CaseStatus
    artifact_type: ArtifactType
    received_at: str
    updated_at: str


class DashboardSeriesPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: str
    high: int = 0
    medium: int = 0
    low: int = 0


class DashboardSummary(BaseModel):
    """Officer dashboard numbers, all computed from the case store."""

    model_config = ConfigDict(extra="forbid")

    days: int
    generated_at: str
    total_cases: int
    cases_in_period: int
    high_risk_in_period: int
    new_today: int
    citizen_reports_new: int
    unreviewed: int
    campaigns: int
    artifact_mix: dict[str, int]
    risk_mix: dict[str, int]
    series: list[DashboardSeriesPoint]
    recent_cases: list[CaseSummary]


class OffenceAct(str, Enum):
    IT_ACT = "IT_ACT"
    BNS = "BNS"
    BOTH = "BOTH"
    UNKNOWN = "UNKNOWN"


class CaseAssignRequest(BaseModel):
    """Assign a case to an officer, optionally recording the offence act."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    assignee_username: str = Field(min_length=3, max_length=64)
    offence_act: OffenceAct | None = None
    reason: str | None = Field(default=None, max_length=500)


class CaseTransferRequest(BaseModel):
    """Move a case to another unit. The reason is mandatory and audited."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    unit_code: str = Field(min_length=2, max_length=40)
    reason: str = Field(min_length=5, max_length=500)


class AuditEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seq: int
    at: str
    actor_name: str
    actor_role: str
    action: str
    target_type: str
    target_id: str
    details: dict = Field(default_factory=dict)


class AuditChainStatus(BaseModel):
    """Whether the audit chain verifies, computed live over the stored rows."""

    model_config = ConfigDict(extra="forbid")

    intact: bool
    events: int
    broken_at: int | None = None
    summary: str


class AuditTrailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: AuditChainStatus
    entries: list[AuditEntry] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase D: action layer - requisitions, approval chain, dispatch, MIS
# ---------------------------------------------------------------------------


class DocumentStatus(str, Enum):
    DRAFT = "DRAFT"
    RETURNED = "RETURNED"
    PENDING_STATION = "PENDING_STATION"
    PENDING_SUPERVISOR = "PENDING_SUPERVISOR"
    APPROVED = "APPROVED"
    DISPATCHED = "DISPATCHED"
    RESPONDED = "RESPONDED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class DispatchChannel(str, Enum):
    EMAIL = "EMAIL"
    PORTAL = "PORTAL"
    POST = "POST"
    HAND = "HAND"


class ApprovalEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: str
    actor_name: str
    actor_rank: str | None = None
    action: str
    comment: str | None = None
    body_sha256: str
    at: str


class DocumentVersionEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int
    body_sha256: str
    at: str


class DocumentSummary(BaseModel):
    """One requisition as the queue and case screens show it."""

    model_config = ConfigDict(extra="forbid")

    id: int
    doc_no: str
    case_id: str
    doc_type: str
    title: str
    legal_basis: str
    addressee_display: str
    addressee_is_sample: bool
    status: DocumentStatus
    current_stage: str
    version: int
    subject_identifiers: list[dict] = Field(default_factory=list)
    created_at: str
    due_at: str | None = None
    overdue: bool = False
    dispatched_at: str | None = None
    dispatch_ref: str | None = None
    dispatch_channel: str | None = None
    response_received_at: str | None = None


class DocumentDetail(DocumentSummary):
    body_html: str
    body_sha256: str
    purpose: str
    sla_hours: float
    response_note: str | None = None
    approvals: list[ApprovalEntry] = Field(default_factory=list)
    versions: list[DocumentVersionEntry] = Field(default_factory=list)
    # True when the body changed after the last approval, so the printed copy
    # is not the one that was signed off.
    edited_after_approval: bool = False


class ActionPackResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    created: int
    existing: int
    documents: list[DocumentSummary] = Field(default_factory=list)
    notice: str


class DocumentEditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    body_html: str = Field(min_length=40, max_length=400_000)


class DocumentCommentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    comment: str | None = Field(default=None, max_length=2_000)


class DocumentReturnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    comment: str = Field(min_length=3, max_length=2_000)


class DocumentDispatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    channel: DispatchChannel = DispatchChannel.EMAIL
    reference: str = Field(min_length=2, max_length=120)


class DocumentResponseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    note: str = Field(min_length=2, max_length=4_000)


class QueueResponse(BaseModel):
    """What is waiting for the signed-in officer, most overdue first."""

    model_config = ConfigDict(extra="forbid")

    stage: str
    total: int
    overdue: int
    documents: list[DocumentSummary] = Field(default_factory=list)


class MisStationRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit_code: str
    unit_name: str
    cases: int
    high_risk: int
    documents: int
    dispatched: int
    overdue: int


class MisReport(BaseModel):
    """The numbers a supervisor sends upward, computed from the case store."""

    model_config = ConfigDict(extra="forbid")

    period: str
    generated_at: str
    scope: str
    cases: int
    high_risk_cases: int
    citizen_reports: int
    amount_reported_paise: int
    documents_drafted: int
    documents_dispatched: int
    documents_answered: int
    documents_overdue: int
    median_hours_to_approval: float | None = None
    by_unit: list[MisStationRow] = Field(default_factory=list)
    top_identifiers: list[dict] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
