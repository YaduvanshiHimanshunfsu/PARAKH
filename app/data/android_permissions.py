from __future__ import annotations

"""Plain-language catalogue of Android permissions for APK reports.

``apk_permission_rules.py`` decides which permissions *score*. This file only
explains what each requested permission lets an app do, so a citizen or an
officer can read the full permission list instead of a raw manifest dump.

Levels follow Android's own protection model:

* ``SPECIAL``   — system-level powers granted through a settings screen
                  (screen overlay, accessibility, device admin, installing apps).
* ``DANGEROUS`` — runtime permissions that touch personal data.
* ``NORMAL``    — granted silently at install; low impact on their own.
* ``UNKNOWN``   — not in this catalogue, or defined by the app itself.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionInfo:
    category: str
    level: str
    description: str


_ANDROID = "android.permission."

_CATALOGUE: dict[str, PermissionInfo] = {
    # SMS
    "READ_SMS": PermissionInfo("SMS", "DANGEROUS", "Read every text message on the phone, including bank OTPs."),
    "RECEIVE_SMS": PermissionInfo("SMS", "DANGEROUS", "See new text messages the moment they arrive — enough to steal an OTP silently."),
    "SEND_SMS": PermissionInfo("SMS", "DANGEROUS", "Send text messages from your number without asking you each time."),
    "RECEIVE_MMS": PermissionInfo("SMS", "DANGEROUS", "Receive and read multimedia messages."),
    "RECEIVE_WAP_PUSH": PermissionInfo("SMS", "DANGEROUS", "Receive WAP push messages sent to the phone."),
    # Contacts and accounts
    "READ_CONTACTS": PermissionInfo("Contacts", "DANGEROUS", "Copy your entire phonebook. Fake loan apps use this to threaten your family and colleagues."),
    "WRITE_CONTACTS": PermissionInfo("Contacts", "DANGEROUS", "Add, change or delete your contacts."),
    "GET_ACCOUNTS": PermissionInfo("Contacts", "DANGEROUS", "List the accounts (Google, WhatsApp, etc.) signed in on the phone."),
    # Calls and phone identity
    "READ_CALL_LOG": PermissionInfo("Calls & phone", "DANGEROUS", "Read who you called, who called you, and when."),
    "WRITE_CALL_LOG": PermissionInfo("Calls & phone", "DANGEROUS", "Change or delete your call history."),
    "PROCESS_OUTGOING_CALLS": PermissionInfo("Calls & phone", "DANGEROUS", "See and redirect the numbers you dial."),
    "CALL_PHONE": PermissionInfo("Calls & phone", "DANGEROUS", "Place phone calls without you dialling, which can cost money."),
    "ANSWER_PHONE_CALLS": PermissionInfo("Calls & phone", "DANGEROUS", "Answer incoming calls on your behalf."),
    "READ_PHONE_STATE": PermissionInfo("Calls & phone", "DANGEROUS", "Read the phone's identity, SIM details and call status."),
    "READ_PHONE_NUMBERS": PermissionInfo("Calls & phone", "DANGEROUS", "Read the phone numbers of the SIM cards in the device."),
    # Location
    "ACCESS_FINE_LOCATION": PermissionInfo("Location", "DANGEROUS", "Track your exact location using GPS."),
    "ACCESS_COARSE_LOCATION": PermissionInfo("Location", "DANGEROUS", "Know your approximate location from mobile towers and Wi-Fi."),
    "ACCESS_BACKGROUND_LOCATION": PermissionInfo("Location", "DANGEROUS", "Keep tracking your location even when the app is closed."),
    # Camera and microphone
    "CAMERA": PermissionInfo("Camera & microphone", "DANGEROUS", "Take photos and videos — fake KYC apps use it to capture your face and ID cards."),
    "RECORD_AUDIO": PermissionInfo("Camera & microphone", "DANGEROUS", "Record sound through the microphone."),
    # Storage and media
    "READ_EXTERNAL_STORAGE": PermissionInfo("Files & media", "DANGEROUS", "Read your photos and files, including pictures of Aadhaar or PAN cards."),
    "WRITE_EXTERNAL_STORAGE": PermissionInfo("Files & media", "DANGEROUS", "Change or delete files stored on the phone."),
    "READ_MEDIA_IMAGES": PermissionInfo("Files & media", "DANGEROUS", "Read the photos stored on the phone."),
    "READ_MEDIA_VIDEO": PermissionInfo("Files & media", "DANGEROUS", "Read the videos stored on the phone."),
    "READ_MEDIA_AUDIO": PermissionInfo("Files & media", "DANGEROUS", "Read audio recordings stored on the phone."),
    "MANAGE_EXTERNAL_STORAGE": PermissionInfo("Files & media", "SPECIAL", "Full access to every file on the phone's storage."),
    # Calendar
    "READ_CALENDAR": PermissionInfo("Calendar", "DANGEROUS", "Read your calendar events and appointments."),
    "WRITE_CALENDAR": PermissionInfo("Calendar", "DANGEROUS", "Add or change calendar events."),
    # Control of the device
    "SYSTEM_ALERT_WINDOW": PermissionInfo("Screen control", "SPECIAL", "Draw on top of other apps — used to place a fake login screen over your real banking app."),
    "BIND_ACCESSIBILITY_SERVICE": PermissionInfo("Screen control", "SPECIAL", "Read everything on your screen and tap buttons for you. The main tool of banking-fraud apps."),
    "BIND_DEVICE_ADMIN": PermissionInfo("Screen control", "SPECIAL", "Become a device administrator, which can lock the phone and block uninstalling."),
    "BIND_NOTIFICATION_LISTENER_SERVICE": PermissionInfo("Screen control", "SPECIAL", "Read every notification, including OTPs shown by other apps."),
    "PACKAGE_USAGE_STATS": PermissionInfo("Screen control", "SPECIAL", "See which apps you use and when."),
    "WRITE_SETTINGS": PermissionInfo("Screen control", "SPECIAL", "Change system settings."),
    "REQUEST_INSTALL_PACKAGES": PermissionInfo("Installing apps", "SPECIAL", "Ask to install other apps from outside the Play Store — typical of a 'dropper'."),
    "REQUEST_DELETE_PACKAGES": PermissionInfo("Installing apps", "NORMAL", "Ask to uninstall other apps."),
    "QUERY_ALL_PACKAGES": PermissionInfo("Installing apps", "SPECIAL", "List every app installed — used to find which banking apps you have."),
    # Background behaviour
    "RECEIVE_BOOT_COMPLETED": PermissionInfo("Background", "NORMAL", "Start automatically every time the phone is switched on."),
    "FOREGROUND_SERVICE": PermissionInfo("Background", "NORMAL", "Keep running in the background with an ongoing notification."),
    "REQUEST_IGNORE_BATTERY_OPTIMIZATIONS": PermissionInfo("Background", "NORMAL", "Ask to be exempted from battery saving so it is never stopped."),
    "WAKE_LOCK": PermissionInfo("Background", "NORMAL", "Keep the phone awake while it works."),
    "POST_NOTIFICATIONS": PermissionInfo("Background", "DANGEROUS", "Show notifications."),
    "DISABLE_KEYGUARD": PermissionInfo("Background", "NORMAL", "Turn off the lock screen."),
    "KILL_BACKGROUND_PROCESSES": PermissionInfo("Background", "NORMAL", "Stop other apps running in the background."),
    # Network and hardware
    "INTERNET": PermissionInfo("Network", "NORMAL", "Send and receive data over the internet."),
    "ACCESS_NETWORK_STATE": PermissionInfo("Network", "NORMAL", "Check whether the phone is online."),
    "ACCESS_WIFI_STATE": PermissionInfo("Network", "NORMAL", "See Wi-Fi connection details."),
    "CHANGE_WIFI_STATE": PermissionInfo("Network", "NORMAL", "Turn Wi-Fi on or off and connect to networks."),
    "NFC": PermissionInfo("Network", "NORMAL", "Use NFC for tap-to-pay or tag reading."),
    "VIBRATE": PermissionInfo("Device", "NORMAL", "Make the phone vibrate."),
    "USE_BIOMETRIC": PermissionInfo("Device", "NORMAL", "Use fingerprint or face unlock to confirm actions."),
    "USE_FINGERPRINT": PermissionInfo("Device", "NORMAL", "Use the fingerprint sensor to confirm actions."),
}

LEVEL_ORDER = {"SPECIAL": 0, "DANGEROUS": 1, "NORMAL": 2, "UNKNOWN": 3}


def describe_permission(permission: str) -> dict:
    """One permission as a row for the report: name, category, level, meaning."""

    if permission.startswith(_ANDROID):
        short = permission[len(_ANDROID):]
        info = _CATALOGUE.get(short)
        if info is not None:
            return {
                "name": permission,
                "short": short,
                "category": info.category,
                "level": info.level,
                "description": info.description,
            }
        return {
            "name": permission,
            "short": short,
            "category": "Other",
            "level": "UNKNOWN",
            "description": "A standard Android permission that is not in PARAKH's reference list.",
        }
    return {
        "name": permission,
        "short": permission.rsplit(".", 1)[-1],
        "category": "App-defined",
        "level": "UNKNOWN",
        "description": "Not a standard Android permission; it is defined by the app or a library it uses.",
    }


def describe_permissions(permissions: list[str]) -> list[dict]:
    """Every requested permission, most powerful first."""

    rows = [describe_permission(name) for name in dict.fromkeys(permissions)]
    rows.sort(key=lambda row: (LEVEL_ORDER[row["level"]], row["category"], row["short"]))
    return rows


__all__ = ["LEVEL_ORDER", "describe_permission", "describe_permissions"]
