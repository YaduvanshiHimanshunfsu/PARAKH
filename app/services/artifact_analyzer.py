from __future__ import annotations

"""Turns a submitted artifact into one ``AnalysisBundle``.

This is the seam between the existing citizen analysers and the investigation
case store. It reuses ``ScamAnalyzer``, ``EmailAnalyzer`` and
``UrlIntelligenceService`` unchanged, then layers on the PS01 additions:
identifier extraction, domain age, redirect resolution, and blacklist matching.

APK (Phase 3) and website (Phase 4) analysis will register here as additional
``artifact_type`` branches, so the dashboard and report paths need no changes.
"""

import logging
from urllib.parse import urlsplit

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.schemas import (
    AnalysisBundle,
    AnalysisResponse,
    AnalyzeRequest,
    ArtifactType,
    EmailAnalyzeRequest,
    Finding,
    Identifier,
    InputLanguage,
    RiskLevel,
    Severity,
    UrlAnalysis,
    UrlRiskLevel,
    Verdict,
)
from app.services.email_analyzer import EmailAnalyzer
from app.services.identifier_extractor import extract_identifiers, merge_identifiers
from app.services.scam_analyzer import ScamAnalyzer
from app.services.url_enrichment import UrlEnrichmentService
from app.utils.fingerprint import content_hash, simhash

logger = logging.getLogger(__name__)

_URL_RISK_SCORE = {
    UrlRiskLevel.CRITICAL: 95,
    UrlRiskLevel.HIGH: 75,
    UrlRiskLevel.MEDIUM: 45,
    UrlRiskLevel.LOW: 10,
    UrlRiskLevel.UNKNOWN: 20,
}

_VERDICT_SCORE = {Verdict.SCAM: 85, Verdict.SUSPICIOUS: 50, Verdict.SAFE: 10}


def _severity_for(level: UrlRiskLevel) -> Severity:
    if level in {UrlRiskLevel.CRITICAL, UrlRiskLevel.HIGH}:
        return Severity.HIGH
    if level is UrlRiskLevel.MEDIUM:
        return Severity.MEDIUM
    return Severity.LOW


def _findings_from_analysis(result: AnalysisResponse) -> list[Finding]:
    """Red flags and URL signals become uniform, queryable findings."""

    findings = [
        Finding(
            code="RED_FLAG",
            severity=Severity.HIGH if result.verdict is Verdict.SCAM else Severity.MEDIUM,
            explanation=flag.explanation,
            evidence=flag.phrase,
        )
        for flag in result.red_flags
    ]
    findings.extend(
        Finding(
            code=f"TACTIC_{tactic.value}",
            severity=Severity.MEDIUM,
            explanation=f"The message uses the {tactic.value.replace('_', ' ').lower()} manipulation tactic.",
            evidence=None,
        )
        for tactic in result.psychological_tactics
    )
    for url in result.url_analyses:
        findings.extend(_findings_from_url(url))
    return findings


def _findings_from_url(url: UrlAnalysis) -> list[Finding]:
    findings = [
        Finding(
            code=signal.code,
            severity=signal.severity,
            explanation=signal.explanation,
            evidence=url.original_url,
        )
        for signal in url.signals
    ]
    for provider in url.reputation:
        if provider.status.value == "FLAGGED":
            findings.append(
                Finding(
                    code="THREAT_INTEL_MATCH",
                    severity=Severity.HIGH,
                    explanation=f"{provider.provider} reports a known threat match for this link.",
                    evidence=url.original_url,
                )
            )
    return findings


class ArtifactAnalyzer:
    """Produces an AnalysisBundle for any submitted artifact type."""

    def __init__(
        self,
        settings: Settings,
        scam_analyzer: ScamAnalyzer,
        email_analyzer: EmailAnalyzer,
        enrichment: UrlEnrichmentService,
    ) -> None:
        self._settings = settings
        self._scam = scam_analyzer
        self._email = email_analyzer
        self._enrichment = enrichment

    async def analyze(
        self,
        artifact_type: ArtifactType,
        content: str,
        *,
        language: InputLanguage = InputLanguage.AUTO,
        session: AsyncSession | None = None,
    ) -> AnalysisBundle:
        if artifact_type is ArtifactType.URL:
            bundle = await self._analyze_url(content, session=session)
        elif artifact_type is ArtifactType.EMAIL:
            bundle = await self._analyze_email(content, language)
        elif artifact_type is ArtifactType.MESSAGE:
            bundle = await self._analyze_message(content, language)
        else:
            raise ValueError(f"{artifact_type.value} analysis is not available yet")

        await self._apply_shared_enrichment(bundle, session=session)
        return bundle

    # --- per-type analysis -------------------------------------------------

    async def _analyze_message(self, content: str, language: InputLanguage) -> AnalysisBundle:
        result = await self._scam.analyze(AnalyzeRequest(message=content, language=language))
        score = _VERDICT_SCORE.get(result.verdict, 20)
        # A high-risk link inside the text raises the case above the text verdict.
        for url in result.url_analyses:
            score = max(score, _URL_RISK_SCORE.get(url.risk_level, 20))
        score = min(100, score + min(15, 3 * len(result.red_flags)))

        return AnalysisBundle(
            artifact_type=ArtifactType.MESSAGE,
            risk_level=self._risk_level(score, result.verdict),
            risk_score=score,
            verdict=result.verdict,
            summary=self._message_summary(result),
            findings=_findings_from_analysis(result),
            identifiers=extract_identifiers(content),
            content_text=content,
            content_sha256=content_hash(content),
            simhash=simhash(content),
            details={
                "scam_category": result.scam_category.value,
                "confidence": result.confidence,
                "analysis_source": result.analysis_source.value,
                "model_used": result.model_used,
                "hindi_summary": result.hindi_summary,
                "action_steps": result.action_steps,
            },
        )

    async def _analyze_url(self, content: str, *, session: AsyncSession | None) -> AnalysisBundle:
        analysis = await self._scam.analyze_url(content)
        score = _URL_RISK_SCORE.get(analysis.risk_level, 20)
        findings = _findings_from_url(analysis)
        identifiers = extract_identifiers(content)
        details: dict = {
            "risk_level": analysis.risk_level.value,
            "registered_domain": analysis.registered_domain,
            "tls_status": analysis.tls.status.value,
            "summary": analysis.summary,
            "limitations": analysis.limitations,
        }

        if analysis.registered_domain:
            age = await self._enrichment.domain_age(analysis.registered_domain, session)
            age_findings = self._enrichment.domain_age_findings(age)
            findings.extend(age_findings)
            details["domain_age_days"] = age.age_days
            details["registrar"] = age.registrar
            if age_findings:
                score = min(100, score + 20)

        chain = await self._enrichment.resolve_redirects(content)
        original_host = urlsplit(analysis.normalized_url or f"https://{content}").hostname
        redirect_findings = self._enrichment.redirect_findings(chain, original_host)
        findings.extend(redirect_findings)
        if chain.hops:
            details["redirect_chain"] = [hop.url for hop in chain.hops]
            details["final_url"] = chain.final_url
        if chain.blocked_reason:
            details["redirect_note"] = chain.blocked_reason
        if redirect_findings:
            score = min(100, score + 15)
            # Identifiers on the destination matter as much as on the entry point.
            if chain.final_url:
                identifiers = merge_identifiers(identifiers, extract_identifiers(chain.final_url))

        return AnalysisBundle(
            artifact_type=ArtifactType.URL,
            risk_level=self._risk_level(score, None),
            risk_score=score,
            verdict=None,
            summary=analysis.summary,
            findings=findings,
            identifiers=identifiers,
            content_text=content,
            content_sha256=content_hash(content),
            simhash=simhash(content),
            details=details,
        )

    async def _analyze_email(self, content: str, language: InputLanguage) -> AnalysisBundle:
        looks_raw = "\n" in content and any(
            header in content[:4_000].lower()
            for header in ("from:", "received:", "subject:", "message-id:")
        )
        request = (
            EmailAnalyzeRequest(raw_eml=content, language=language)
            if looks_raw
            else EmailAnalyzeRequest(body=content, language=language)
        )
        result = await self._email.analyze(request)
        score = _VERDICT_SCORE.get(result.verdict, 20)
        score = min(100, max(score, result.confidence if result.verdict is not Verdict.SAFE else 10))

        findings = [
            Finding(
                code="RED_FLAG",
                severity=Severity.HIGH if result.verdict is Verdict.SCAM else Severity.MEDIUM,
                explanation=flag.explanation,
                evidence=flag.phrase,
            )
            for flag in result.red_flags
        ]
        for name, status in (
            ("SPF", result.authentication.spf),
            ("DKIM", result.authentication.dkim),
            ("DMARC", result.authentication.dmarc),
        ):
            if status.value in {"FAIL", "SOFTFAIL"}:
                findings.append(
                    Finding(
                        code=f"EMAIL_AUTH_{name}_FAIL",
                        severity=Severity.HIGH,
                        explanation=f"{name} authentication did not pass for this email.",
                        evidence=f"{name}={status.value}",
                    )
                )
        for attachment in result.attachments:
            if attachment.risk in {UrlRiskLevel.HIGH, UrlRiskLevel.CRITICAL}:
                findings.append(
                    Finding(
                        code="DANGEROUS_ATTACHMENT",
                        severity=Severity.HIGH,
                        explanation=attachment.reason,
                        evidence=attachment.filename,
                    )
                )
        for url in result.url_analyses:
            findings.extend(_findings_from_url(url))

        return AnalysisBundle(
            artifact_type=ArtifactType.EMAIL,
            risk_level=self._risk_level(score, result.verdict),
            risk_score=score,
            verdict=result.verdict,
            summary=f"{result.email_type.value.replace('_', ' ').title()} — {result.verdict.value}",
            findings=findings,
            identifiers=extract_identifiers(content),
            content_text=content,
            content_sha256=content_hash(content),
            simhash=simhash(content),
            details={
                "email_type": result.email_type.value,
                "scam_category": result.scam_category.value,
                "confidence": result.confidence,
                "sender": result.sender.address,
                "reply_to": result.reply_to.address if result.reply_to else None,
                "spf": result.authentication.spf.value,
                "dkim": result.authentication.dkim.value,
                "dmarc": result.authentication.dmarc.value,
                "limitations": result.limitations,
            },
        )

    # --- shared enrichment --------------------------------------------------

    async def _apply_shared_enrichment(
        self, bundle: AnalysisBundle, *, session: AsyncSession | None
    ) -> None:
        """Blacklist matching applies to every artifact type identically."""

        if session is None or not bundle.identifiers:
            return
        matches = await self._enrichment.match_blacklist(session, bundle.identifiers)
        if not matches:
            return
        bundle.findings.extend(matches)
        bundle.risk_score = min(100, max(bundle.risk_score, 80))
        bundle.risk_level = RiskLevel.HIGH

    @staticmethod
    def _risk_level(score: int, verdict: Verdict | None) -> RiskLevel:
        from app.services.case_service import derive_risk_level

        return derive_risk_level(score, verdict)

    @staticmethod
    def _message_summary(result: AnalysisResponse) -> str:
        category = result.scam_category.value.replace("_", " ").title()
        return f"{category} — {result.verdict.value} ({result.confidence}% confidence)"
