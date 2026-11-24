from __future__ import annotations

"""Deterministic APK risk assessment.

Produces the same ``AnalysisBundle`` shape as every other analyser, so an APK
case lands in the investigation dashboard, the identifier graph, and the report
builder with no special-casing downstream.

No AI provider is involved. The baseline test in Phase 0 showed the live Gemini
key failing with HTTP 401 while the rule engine still returned a correct
verdict; APK analysis is built to that standard from the start (ADR-005).
"""

import logging
import re

from app.data.android_permissions import describe_permissions
from app.data.apk_permission_rules import (
    BANKING_TROJAN_CAPABILITIES,
    COMBINATION_RULES,
    DECLARED_CAPABILITY_RULES,
    MIN_EXPECTED_TARGET_SDK,
    SINGLE_PERMISSION_RULES,
    SMS_INTERCEPT_PRIORITY,
)
from app.schemas import (
    AnalysisBundle,
    ArtifactType,
    Finding,
    Identifier,
    IdentifierType,
    RiskLevel,
    Severity,
)
from app.services.apk_parsing import ApkFacts, ApkParsingError, inspect_apk
from app.services.identifier_extractor import extract_identifiers, merge_identifiers

logger = logging.getLogger(__name__)

# Well-known Indian finance and government brands. An app whose label copies
# one of these while its package namespace does not belong to the brand is a
# likely impersonation.
_PROTECTED_BRANDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("sbi", ("com.sbi", "in.co.sbi", "com.statebank")),
    ("hdfc", ("com.snapwork.hdfc", "com.hdfcbank")),
    ("icici", ("com.csam.icici", "com.icicibank")),
    ("axis", ("com.axis",)),
    ("kotak", ("com.msf.kbank", "com.kotak")),
    ("paytm", ("net.one97.paytm",)),
    ("phonepe", ("com.phonepe",)),
    ("bhim", ("in.org.npci",)),
    ("aadhaar", ("in.gov.uidai",)),
    ("uidai", ("in.gov.uidai",)),
    ("irctc", ("cris.org.in", "com.irctc")),
    ("rbi", ("in.gov.rbi", "com.rbi")),
)

# Loan/finance vocabulary in a package or label. Harmless alone; meaningful
# when the app also demands SMS and contacts access. Matched as whole tokens,
# never substrings — 'earn' must not match 'learn'.
_FINANCE_TERMS = frozenset({
    "loan", "loans", "credit", "cash", "rupee", "rupees", "paisa", "lend",
    "lending", "borrow", "emi", "finance", "financial", "fund", "funds",
    "money", "wallet", "pay", "invest", "investment", "profit", "earn",
    "earning", "earnings", "capital", "advance",
})

_MAX_IDENTIFIER_STRINGS = 4_000
_MAX_COMPONENT_NAMES = 40


def _declared_findings(facts: ApkFacts) -> tuple[list[Finding], int]:
    """Findings for capabilities declared on manifest components (B.7 step 2)."""

    findings: list[Finding] = []
    score = 0
    declared = facts.declared or {}

    for rule in DECLARED_CAPABILITY_RULES:
        if declared.get(rule.key):
            findings.append(
                Finding(
                    code=rule.code,
                    severity=rule.severity,
                    explanation=rule.explanation,
                    evidence=f"<{rule.key}> declared in AndroidManifest.xml",
                )
            )
            score += rule.weight

    priority = facts.sms_receiver_priority
    if declared.get("sms_receiver"):
        high_priority = priority is not None and priority >= SMS_INTERCEPT_PRIORITY
        findings.append(
            Finding(
                code="SMS_INTERCEPT_RECEIVER" if high_priority else "SMS_RECEIVER_DECLARED",
                severity=Severity.HIGH if high_priority else Severity.MEDIUM,
                explanation=(
                    "The app registers a high-priority receiver for incoming SMS, so it reads "
                    "messages before the normal messaging app and can hide bank OTPs."
                    if high_priority
                    else "The app receives incoming SMS, which includes bank OTPs."
                ),
                evidence=f"SMS_RECEIVED priority={priority}" if priority is not None else "SMS_RECEIVED receiver",
            )
        )
        score += 30 if high_priority else 18

    present = {key for key, value in declared.items() if value}
    if BANKING_TROJAN_CAPABILITIES <= present:
        findings.append(
            Finding(
                code="BANKING_TROJAN_SIGNATURE",
                severity=Severity.HIGH,
                explanation=(
                    "This app combines screen-reading accessibility access with SMS interception. "
                    "Together these are the defining capabilities of an Android banking trojan: "
                    "it can see what you type and silently capture the OTP."
                ),
                evidence=", ".join(sorted(BANKING_TROJAN_CAPABILITIES & present)),
            )
        )
        score += 30

    return findings, score


class ApkAnalyzer:
    """Static APK analysis producing an explainable Low/Medium/High verdict."""

    def analyze(self, data: bytes, filename: str | None = None) -> AnalysisBundle:
        facts = inspect_apk(data)

        findings: list[Finding] = []
        score = 0

        permission_findings, permission_score = self._permission_findings(facts)
        findings.extend(permission_findings)
        score += permission_score

        manifest_findings, manifest_score = self._manifest_findings(facts)
        findings.extend(manifest_findings)
        score += manifest_score

        certificate_findings, certificate_score = self._certificate_findings(facts)
        findings.extend(certificate_findings)
        score += certificate_score

        identifiers, network_findings, network_score = self._network_findings(facts)
        findings.extend(network_findings)
        score += network_score

        brand_findings, brand_score = self._impersonation_findings(facts)
        findings.extend(brand_findings)
        score += brand_score

        score = max(0, min(100, score))
        return AnalysisBundle(
            artifact_type=ArtifactType.APK,
            risk_level=self._risk_level(score),
            risk_score=score,
            verdict=None,
            summary=self._summary(facts, score),
            findings=findings[:60],
            identifiers=identifiers,
            content_text=self._evidence_text(facts, filename),
            content_sha256=facts.sha256,
            simhash=None,
            details=self._details(facts, filename),
        )

    # --- permissions -------------------------------------------------------

    def _permission_findings(self, facts: ApkFacts) -> tuple[list[Finding], int]:
        if not facts.permissions:
            return [], 0

        held = set(facts.permissions)
        findings: list[Finding] = []
        score = 0

        for rule in SINGLE_PERMISSION_RULES:
            if rule.permission in held:
                findings.append(
                    Finding(
                        code=rule.code,
                        severity=rule.severity,
                        explanation=rule.explanation,
                        evidence=rule.permission,
                    )
                )
                score += rule.weight

        # Combinations are scored on top: the whole is worse than the parts.
        for combo in COMBINATION_RULES:
            if combo.permissions <= held:
                findings.append(
                    Finding(
                        code=combo.code,
                        severity=combo.severity,
                        explanation=combo.explanation,
                        evidence=", ".join(sorted(combo.permissions)),
                    )
                )
                score += combo.weight

        return findings, score

    # --- manifest ----------------------------------------------------------

    @staticmethod
    def _manifest_findings(facts: ApkFacts) -> tuple[list[Finding], int]:
        findings: list[Finding] = []
        score = 0

        if not facts.manifest_parsed:
            findings.append(
                Finding(
                    code="MANIFEST_UNREADABLE",
                    severity=Severity.MEDIUM,
                    explanation=(
                        "The AndroidManifest could not be decoded. A deliberately malformed manifest "
                        "is sometimes used to defeat automated inspection."
                    ),
                    evidence=None,
                )
            )
            return findings, 15

        if facts.target_sdk is not None and facts.target_sdk < MIN_EXPECTED_TARGET_SDK:
            findings.append(
                Finding(
                    code="LOW_TARGET_SDK",
                    severity=Severity.MEDIUM,
                    explanation=(
                        f"The app targets Android API {facts.target_sdk}, below the modern baseline of "
                        f"{MIN_EXPECTED_TARGET_SDK}. A low target lets an app bypass runtime permission "
                        "prompts and scoped storage protections."
                    ),
                    evidence=f"targetSdkVersion={facts.target_sdk}",
                )
            )
            score += 18

        findings_declared, declared_score = _declared_findings(facts)
        findings.extend(findings_declared)
        score += declared_score

        return findings, score

    # --- certificate -------------------------------------------------------

    @staticmethod
    def _certificate_findings(facts: ApkFacts) -> tuple[list[Finding], int]:
        certificate = facts.certificate
        findings: list[Finding] = []
        score = 0

        if facts.packers:
            findings.append(
                Finding(
                    code="PACKED_APP",
                    severity=Severity.MEDIUM,
                    explanation=(
                        "The app is protected by a commercial packer, so its real code is only "
                        "unpacked while running. Static inspection cannot see what it does. "
                        "Packers have legitimate uses, but they also hide malware."
                    ),
                    evidence=", ".join(facts.packers)[:200],
                )
            )
            score += 12

        if certificate.sha256 is None:
            findings.append(
                Finding(
                    code="UNSIGNED_OR_UNREADABLE_SIGNATURE",
                    severity=Severity.HIGH,
                    explanation=(
                        "No readable signing certificate was found. A legitimately distributed app is "
                        "always signed, and the signature is what ties it to a publisher."
                    ),
                    evidence=None,
                )
            )
            return findings, 25

        if certificate.debug_certificate:
            findings.append(
                Finding(
                    code="DEBUG_CERTIFICATE",
                    severity=Severity.HIGH,
                    explanation=(
                        "The app is signed with the Android debug key. Debug-signed builds cannot be "
                        "published on Google Play and indicate sideloaded distribution."
                    ),
                    evidence=certificate.subject,
                )
            )
            score += 32
        elif certificate.self_signed:
            findings.append(
                Finding(
                    code="SELF_SIGNED_CERTIFICATE",
                    severity=Severity.LOW,
                    explanation=(
                        "The signing certificate is self-signed. This is normal for Android, so it is "
                        "recorded as context rather than treated as a problem on its own."
                    ),
                    evidence=certificate.subject,
                )
            )

        if certificate.validity_days is not None and certificate.validity_days < 365:
            findings.append(
                Finding(
                    code="SHORT_LIVED_CERTIFICATE",
                    severity=Severity.MEDIUM,
                    explanation=(
                        f"The signing certificate is valid for only {certificate.validity_days} days. "
                        "Google Play requires validity until at least 2033, so a short window suggests "
                        "the app was never intended for the official store."
                    ),
                    evidence=f"validity={certificate.validity_days} days",
                )
            )
            score += 20

        return findings, score

    # --- embedded network indicators ---------------------------------------

    def _network_findings(self, facts: ApkFacts) -> tuple[list[Identifier], list[Finding], int]:
        """Run embedded strings through the shared extractor.

        Using the same extractor as messages and websites is what lets a C2 host
        or UPI ID inside an APK link to the same value found in an SMS.
        """

        findings: list[Finding] = []
        score = 0

        blob = "\n".join(facts.extracted_strings[:_MAX_IDENTIFIER_STRINGS])
        identifiers = extract_identifiers(blob, include_context=False) if blob else []

        if facts.package:
            identifiers = merge_identifiers(
                identifiers,
                [
                    Identifier(
                        type=IdentifierType.PACKAGE,
                        value=facts.package.lower(),
                        raw_value=facts.package,
                        context="Declared package name",
                        confidence=100,
                    )
                ],
            )
        if facts.certificate.sha256:
            identifiers = merge_identifiers(
                identifiers,
                [
                    Identifier(
                        type=IdentifierType.CERT_SHA256,
                        value=facts.certificate.sha256,
                        raw_value=facts.certificate.sha256,
                        context="APK signing certificate fingerprint",
                        confidence=100,
                    )
                ],
            )
        if facts.icon_dhash:
            identifiers = merge_identifiers(
                identifiers,
                [
                    Identifier(
                        type=IdentifierType.ICON_PHASH,
                        value=facts.icon_dhash,
                        raw_value=facts.icon_dhash,
                        context="Launcher icon perceptual hash",
                        confidence=100,
                    )
                ],
            )

        hardcoded_ips = [item for item in identifiers if item.type is IdentifierType.IP]
        if hardcoded_ips:
            findings.append(
                Finding(
                    code="HARDCODED_IP_ENDPOINT",
                    severity=Severity.HIGH,
                    explanation=(
                        "The app contains hard-coded public IP addresses. Legitimate apps call named "
                        "domains; raw IPs are typical of throwaway command-and-control servers."
                    ),
                    evidence=", ".join(item.value for item in hardcoded_ips[:5]),
                )
            )
            score += 22

        payment_identifiers = [
            item
            for item in identifiers
            if item.type
            in {
                IdentifierType.UPI,
                IdentifierType.CRYPTO_BTC,
                IdentifierType.CRYPTO_ETH,
                IdentifierType.BANK_ACCOUNT,
                IdentifierType.IFSC,
            }
        ]
        if payment_identifiers:
            findings.append(
                Finding(
                    code="EMBEDDED_PAYMENT_IDENTIFIER",
                    severity=Severity.HIGH,
                    explanation=(
                        "Payment identifiers are embedded in the app package. These are directly "
                        "actionable for tracing where collected money goes."
                    ),
                    evidence=", ".join(
                        f"{item.type.value}:{item.value}" for item in payment_identifiers[:5]
                    ),
                )
            )
            score += 25

        telegram = [item for item in identifiers if item.type is IdentifierType.TELEGRAM]
        if telegram:
            findings.append(
                Finding(
                    code="EMBEDDED_TELEGRAM_CHANNEL",
                    severity=Severity.MEDIUM,
                    explanation=(
                        "The app embeds Telegram links. Fraudulent loan, investment, and betting apps "
                        "routinely move victims to Telegram to avoid moderated platforms."
                    ),
                    evidence=", ".join(item.value for item in telegram[:5]),
                )
            )
            score += 15

        plaintext_endpoints = [
            item.value
            for item in identifiers
            if item.type is IdentifierType.URL and item.value.startswith("http://")
        ]
        if plaintext_endpoints:
            findings.append(
                Finding(
                    code="CLEARTEXT_ENDPOINT",
                    severity=Severity.MEDIUM,
                    explanation=(
                        "The app contains unencrypted http:// endpoints, so data it sends can be read "
                        "or modified in transit."
                    ),
                    evidence=", ".join(plaintext_endpoints[:5]),
                )
            )
            score += 12

        return identifiers, findings, score

    # --- brand impersonation ------------------------------------------------

    @staticmethod
    def _tokens(facts: ApkFacts) -> set[str]:
        """Split the label and package into whole words and package segments.

        Substring matching is not usable here: 'rbi' appears inside 'orbit',
        'axis' inside 'taxis', and 'earn' inside 'learn'. Matching on token
        boundaries is what keeps an ordinary app off the impersonation list.
        """

        raw = f"{facts.app_label or ''} {facts.package or ''}".casefold()
        return {token for token in re.split(r"[^a-z0-9]+", raw) if token}

    @staticmethod
    def _impersonation_findings(facts: ApkFacts) -> tuple[list[Finding], int]:
        findings: list[Finding] = []
        score = 0

        package = (facts.package or "").casefold()
        tokens = ApkAnalyzer._tokens(facts)

        for brand, official_prefixes in _PROTECTED_BRANDS:
            if brand not in tokens:
                continue
            if any(package.startswith(prefix) for prefix in official_prefixes):
                continue
            findings.append(
                Finding(
                    code="BRAND_IMPERSONATION",
                    severity=Severity.HIGH,
                    explanation=(
                        f"The app references '{brand}' but its package '{facts.package or 'unknown'}' is "
                        "not one published by that organisation. Verify the publisher on the official "
                        "store listing before trusting it."
                    ),
                    evidence=f"label={facts.app_label!r} package={facts.package!r}",
                )
            )
            score += 30
            break

        finance_app = bool(tokens & _FINANCE_TERMS)
        held = set(facts.permissions)
        sensitive = {"android.permission.READ_SMS", "android.permission.READ_CONTACTS"}
        if finance_app and sensitive & held:
            findings.append(
                Finding(
                    code="FINANCE_APP_SENSITIVE_PERMISSIONS",
                    severity=Severity.HIGH,
                    explanation=(
                        "The app presents itself as a finance or lending app and also requests SMS or "
                        "contacts access. An RBI-regulated lender does not need either to assess a loan."
                    ),
                    evidence=f"label={facts.app_label!r} permissions={sorted(sensitive & held)}",
                )
            )
            score += 25

        return findings, score

    # --- presentation -------------------------------------------------------

    @staticmethod
    def _risk_level(score: int) -> RiskLevel:
        if score >= 70:
            return RiskLevel.HIGH
        if score >= 35:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    @staticmethod
    def _summary(facts: ApkFacts, score: int) -> str:
        name = facts.app_label or facts.package or "Unknown app"
        package = facts.package or "unknown package"
        return f"{name} ({package}) — static APK analysis, risk score {score}/100"

    @staticmethod
    def _evidence_text(facts: ApkFacts, filename: str | None) -> str:
        """Searchable text representation of the package for the dashboard."""

        lines = [
            f"APK: {filename or 'upload'}",
            f"SHA-256: {facts.sha256}",
            f"Package: {facts.package or 'unknown'}",
            f"Label: {facts.app_label or 'unknown'}",
            f"Version: {facts.version_name or '?'} ({facts.version_code or '?'})",
            f"SDK: min={facts.min_sdk} target={facts.target_sdk}",
            f"Certificate: {facts.certificate.subject or 'unreadable'}",
            f"Certificate SHA-256: {facts.certificate.sha256 or 'none'}",
            "Permissions:",
            *(f"  - {permission}" for permission in facts.permissions),
        ]
        return "\n".join(lines)[:200_000]

    @staticmethod
    def _details(facts: ApkFacts, filename: str | None) -> dict:
        certificate = facts.certificate
        return {
            "filename": filename,
            "sha256": facts.sha256,
            "size_bytes": facts.size_bytes,
            "package": facts.package,
            "app_label": facts.app_label,
            "version_name": facts.version_name,
            "version_code": facts.version_code,
            "min_sdk": facts.min_sdk,
            "target_sdk": facts.target_sdk,
            "permissions": facts.permissions,
            "permission_count": len(facts.permissions),
            "permission_profile": describe_permissions(facts.permissions),
            "activity_count": len(facts.activities),
            "service_count": len(facts.services),
            "receiver_count": len(facts.receivers),
            "services": facts.services[:_MAX_COMPONENT_NAMES],
            "receivers": facts.receivers[:_MAX_COMPONENT_NAMES],
            "dex_count": facts.dex_count,
            "entry_count": facts.entry_count,
            "certificate": {
                "sha256": certificate.sha256,
                "subject": certificate.subject,
                "issuer": certificate.issuer,
                "self_signed": certificate.self_signed,
                "debug_certificate": certificate.debug_certificate,
                "validity_days": certificate.validity_days,
            },
            "icon_dhash": facts.icon_dhash,
            "limitations": facts.limitations,
            "manifest_parsed": facts.manifest_parsed,
        }


__all__ = ["ApkAnalyzer", "ApkParsingError"]
