from __future__ import annotations

"""Reviewed Android permission risk rules.

PS01 calls out inspecting "APK permissions (contacts, SMS, camera)". The signal
that actually identifies a predatory loan app is not any single permission but
a *combination*: reading SMS (to intercept bank OTPs) plus reading contacts (to
harass the borrower's phonebook during recovery) plus internet (to exfiltrate
both). Each permission alone is unremarkable; together they are the documented
signature of the fraud family PS01 describes.

Rules are version-controlled data, like ``scam_rules.py``, so every APK verdict
cites a reviewed rule rather than an opaque score.
"""

from dataclasses import dataclass

from app.schemas import Severity

P = "android.permission."


@dataclass(frozen=True)
class PermissionRule:
    """A single permission that carries risk on its own."""

    permission: str
    code: str
    severity: Severity
    weight: int
    explanation: str


@dataclass(frozen=True)
class PermissionComboRule:
    """A combination that is far more serious than its parts."""

    permissions: frozenset[str]
    code: str
    severity: Severity
    weight: int
    explanation: str


SINGLE_PERMISSION_RULES: tuple[PermissionRule, ...] = (
    PermissionRule(
        f"{P}READ_SMS", "PERM_READ_SMS", Severity.HIGH, 30,
        "The app can read every SMS on the device, including banking OTPs. Very few legitimate "
        "apps need this, and Google Play restricts it.",
    ),
    PermissionRule(
        f"{P}RECEIVE_SMS", "PERM_RECEIVE_SMS", Severity.HIGH, 26,
        "The app is notified of incoming SMS as they arrive, which allows silent OTP interception.",
    ),
    PermissionRule(
        f"{P}READ_CONTACTS", "PERM_READ_CONTACTS", Severity.HIGH, 24,
        "The app can copy the entire phonebook. Predatory loan apps harvest contacts to threaten "
        "borrowers' family and colleagues during recovery.",
    ),
    PermissionRule(
        f"{P}READ_CALL_LOG", "PERM_READ_CALL_LOG", Severity.HIGH, 22,
        "The app can read who the user calls and when — a privacy-invasive permission with no "
        "legitimate use in a finance or utility app.",
    ),
    PermissionRule(
        f"{P}BIND_ACCESSIBILITY_SERVICE", "PERM_ACCESSIBILITY", Severity.HIGH, 38,
        "Accessibility access lets the app read screen content and perform taps on the user's "
        "behalf. It is the permission behind most Android banking-overlay fraud.",
    ),
    PermissionRule(
        f"{P}SYSTEM_ALERT_WINDOW", "PERM_OVERLAY", Severity.HIGH, 28,
        "The app can draw over other apps, which enables a fake login screen on top of a real "
        "banking app.",
    ),
    PermissionRule(
        f"{P}REQUEST_INSTALL_PACKAGES", "PERM_INSTALL_PACKAGES", Severity.HIGH, 30,
        "The app can prompt to install other APKs, which is dropper behaviour.",
    ),
    PermissionRule(
        f"{P}SEND_SMS", "PERM_SEND_SMS", Severity.HIGH, 24,
        "The app can send SMS without the user, enabling premium-rate billing or spreading itself "
        "to the victim's contacts.",
    ),
    PermissionRule(
        f"{P}CAMERA", "PERM_CAMERA", Severity.MEDIUM, 12,
        "The app can capture photos and video. Combined with storage access this supports KYC "
        "document and selfie harvesting.",
    ),
    PermissionRule(
        f"{P}RECORD_AUDIO", "PERM_RECORD_AUDIO", Severity.MEDIUM, 16,
        "The app can record audio, including calls in progress on some devices.",
    ),
    PermissionRule(
        f"{P}ACCESS_FINE_LOCATION", "PERM_FINE_LOCATION", Severity.MEDIUM, 12,
        "The app can track precise location, used by recovery agents to pressure borrowers.",
    ),
    PermissionRule(
        f"{P}READ_EXTERNAL_STORAGE", "PERM_READ_STORAGE", Severity.MEDIUM, 10,
        "The app can read stored files, including photographs of identity documents.",
    ),
    PermissionRule(
        f"{P}READ_PHONE_STATE", "PERM_PHONE_STATE", Severity.LOW, 8,
        "The app can read device and SIM identifiers, which supports persistent tracking.",
    ),
    PermissionRule(
        f"{P}QUERY_ALL_PACKAGES", "PERM_QUERY_PACKAGES", Severity.MEDIUM, 12,
        "The app can enumerate every installed app, commonly used to detect which banking apps "
        "are present before showing a matching fake screen.",
    ),
)


COMBINATION_RULES: tuple[PermissionComboRule, ...] = (
    PermissionComboRule(
        frozenset({f"{P}READ_SMS", f"{P}READ_CONTACTS", f"{P}INTERNET"}),
        "COMBO_LOAN_APP_HARVESTING", Severity.HIGH, 45,
        "The app can read SMS, copy the phonebook, and send both to a server. This is the "
        "defining permission signature of a predatory instant-loan app: OTP interception plus "
        "contact harvesting for harassment-based recovery.",
    ),
    PermissionComboRule(
        frozenset({f"{P}BIND_ACCESSIBILITY_SERVICE", f"{P}SYSTEM_ALERT_WINDOW"}),
        "COMBO_OVERLAY_TAKEOVER", Severity.HIGH, 50,
        "The app can both draw over other apps and act on the user's behalf. Together these allow "
        "a convincing fake banking screen that can also approve transactions.",
    ),
    PermissionComboRule(
        frozenset({f"{P}RECEIVE_SMS", f"{P}INTERNET"}),
        "COMBO_OTP_EXFILTRATION", Severity.HIGH, 35,
        "The app can intercept incoming SMS and immediately forward them, which is how banking "
        "OTPs are stolen without the victim noticing.",
    ),
    PermissionComboRule(
        frozenset({f"{P}CAMERA", f"{P}READ_EXTERNAL_STORAGE", f"{P}INTERNET"}),
        "COMBO_KYC_DOCUMENT_HARVESTING", Severity.MEDIUM, 22,
        "The app can capture images, read stored files, and upload them — the pattern used to "
        "collect Aadhaar, PAN, and selfie images under the guise of KYC.",
    ),
    PermissionComboRule(
        frozenset({f"{P}REQUEST_INSTALL_PACKAGES", f"{P}INTERNET"}),
        "COMBO_DROPPER", Severity.HIGH, 38,
        "The app can download and prompt installation of further APKs, allowing the real payload "
        "to arrive after the initial install passes review.",
    ),
    PermissionComboRule(
        frozenset({f"{P}READ_CALL_LOG", f"{P}READ_CONTACTS", f"{P}ACCESS_FINE_LOCATION"}),
        "COMBO_BORROWER_SURVEILLANCE", Severity.HIGH, 32,
        "The app can build a profile of who the user contacts, calls, and where they are — the "
        "toolkit used to pressure borrowers rather than to provide a service.",
    ),
)


# Permissions that are unremarkable in most apps but notable in a finance app
# that claims to only display information.
DANGEROUS_PERMISSIONS: frozenset[str] = frozenset(
    rule.permission for rule in SINGLE_PERMISSION_RULES if rule.severity is Severity.HIGH
)


# A low targetSdk lets an app opt out of modern runtime-permission prompts and
# scoped storage. Android 10 (API 29) is the practical floor for a current app.
MIN_EXPECTED_TARGET_SDK = 29
