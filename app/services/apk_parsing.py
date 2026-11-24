from __future__ import annotations

"""Static APK inspection primitives.

Static only — the APK is never installed, executed, or unpacked to a path a
loader could reach. Dynamic sandbox analysis is explicitly out of PS01 scope.

Everything here is deterministic and offline: no AI provider, no network, no
third-party scanning service (DECISIONS.md ADR-005). An obfuscated or packed
APK yields fewer strings, and that is reported as a limitation rather than
silently producing a confident-looking empty result.
"""

import hashlib
import io
import logging
import re
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

ZIP_MAGIC = b"PK\x03\x04"
_REQUIRED_ENTRIES = ("AndroidManifest.xml",)

# A zip bomb is the realistic hostile input here: a small archive that expands
# to gigabytes. Reject on both absolute size and compression ratio.
_MAX_UNCOMPRESSED_BYTES = 600_000_000
_MAX_COMPRESSION_RATIO = 120
_MAX_ENTRIES = 20_000

# Printable ASCII runs inside DEX/resource blobs. 6 is long enough to skip
# opcode noise and short enough to catch hosts like "a.cc".
_ASCII_STRING_RE = re.compile(rb"[\x20-\x7e]{6,400}")
_MAX_SCANNED_BYTES = 48_000_000
_MAX_STRINGS = 60_000

_DEBUG_CERT_MARKERS = ("androiddebugkey", "android debug", "cn=android debug")


class ApkParsingError(ValueError):
    """The upload is not a usable Android package."""


@dataclass
class ApkCertificate:
    sha256: str | None = None
    subject: str | None = None
    issuer: str | None = None
    not_before: datetime | None = None
    not_after: datetime | None = None
    self_signed: bool = False
    debug_certificate: bool = False
    validity_days: int | None = None
    # Which APK Signature Schemes are present. v2/v3-only packages used to be
    # reported as unsigned (defect D9).
    schemes: list[str] = field(default_factory=list)


@dataclass
class ApkFacts:
    """Everything extracted from one APK, before any risk judgement."""

    size_bytes: int
    sha256: str
    package: str | None = None
    app_label: str | None = None
    version_name: str | None = None
    version_code: str | None = None
    min_sdk: int | None = None
    target_sdk: int | None = None
    permissions: list[str] = field(default_factory=list)
    activities: list[str] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    receivers: list[str] = field(default_factory=list)
    certificate: ApkCertificate = field(default_factory=ApkCertificate)
    icon_dhash: str | None = None
    dex_count: int = 0
    entry_count: int = 0
    extracted_strings: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    manifest_parsed: bool = False
    # Capabilities declared at component level rather than by a permission:
    # real banking trojans bind the accessibility and notification-listener
    # services and register a high-priority SMS receiver (defect D8).
    declared: dict[str, bool] = field(default_factory=dict)
    sms_receiver_priority: int | None = None
    packers: list[str] = field(default_factory=list)
    split_names: list[str] = field(default_factory=list)


# --- container validation --------------------------------------------------


def validate_apk_container(data: bytes) -> zipfile.ZipFile:
    """Confirm the upload is a sane APK zip before anything reads its contents."""

    if len(data) < len(ZIP_MAGIC) or not data.startswith(ZIP_MAGIC):
        raise ApkParsingError("This file is not an Android package (APK).")

    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ApkParsingError("The APK archive is corrupt or unreadable.") from exc

    infos = archive.infolist()
    if len(infos) > _MAX_ENTRIES:
        raise ApkParsingError("The archive contains an implausible number of entries.")

    total_uncompressed = sum(info.file_size for info in infos)
    if total_uncompressed > _MAX_UNCOMPRESSED_BYTES:
        raise ApkParsingError("The archive expands to an unsafe size and was not inspected.")
    if len(data) and total_uncompressed / max(1, len(data)) > _MAX_COMPRESSION_RATIO:
        raise ApkParsingError("The archive has an unsafe compression ratio and was not inspected.")

    names = {info.filename for info in infos}
    missing = [entry for entry in _REQUIRED_ENTRIES if entry not in names]
    if missing:
        raise ApkParsingError("The archive is missing AndroidManifest.xml, so it is not a valid APK.")

    return archive


# --- manifest --------------------------------------------------------------


def parse_manifest(data: bytes, facts: ApkFacts) -> None:
    """Populate package metadata and permissions via pyaxmlparser.

    Manifest parsing is the one step with a third-party dependency, so failure
    degrades to a limitation: string, certificate and icon analysis still run.
    """

    try:
        from pyaxmlparser import APK  # imported lazily so the module loads without it
    except ImportError:
        facts.limitations.append(
            "Manifest parsing is unavailable because pyaxmlparser is not installed."
        )
        return

    try:
        apk = APK(data, raw=True)
        facts.package = _clean(apk.package)
        facts.app_label = _clean(apk.get_app_name())
        facts.version_name = _clean(apk.get_androidversion_name())
        facts.version_code = _clean(apk.get_androidversion_code())
        facts.permissions = sorted({p for p in (apk.get_permissions() or []) if p})
        facts.activities = [a for a in (apk.get_activities() or []) if a][:60]
        facts.services = [s for s in (apk.get_services() or []) if s][:60]
        facts.receivers = [r for r in (apk.get_receivers() or []) if r][:60]
        facts.min_sdk = _as_int(apk.get_min_sdk_version())
        facts.target_sdk = _as_int(apk.get_target_sdk_version())
        facts.manifest_parsed = True
        _parse_components(apk, facts)
    except Exception as exc:
        logger.warning("apk_manifest_parse_failed error=%s", type(exc).__name__)
        facts.limitations.append(
            "The AndroidManifest could not be decoded. Package name, permissions and components "
            "are unavailable; this can indicate an obfuscated or deliberately malformed APK."
        )


_ANDROID_NS = "{http://schemas.android.com/apk/res/android}"

# Component-level declarations worth naming. Each is a capability a banking
# trojan needs and an ordinary app almost never does.
_BIND_PERMISSIONS = {
    "android.permission.BIND_ACCESSIBILITY_SERVICE": "accessibility_service",
    "android.permission.BIND_NOTIFICATION_LISTENER_SERVICE": "notification_listener",
    "android.permission.BIND_DEVICE_ADMIN": "device_admin",
}
_INTENT_ACTIONS = {
    "android.accessibilityservice.AccessibilityService": "accessibility_service",
    "android.service.notification.NotificationListenerService": "notification_listener",
    "android.app.action.DEVICE_ADMIN_ENABLED": "device_admin",
    "android.provider.Telephony.SMS_RECEIVED": "sms_receiver",
    "android.provider.Telephony.SMS_DELIVER": "default_sms_app",
    "android.intent.action.BOOT_COMPLETED": "boot_persistence",
}

# Native libraries and assets left behind by common commercial packers.
_PACKER_MARKERS = {
    "libjiagu": "Qihoo 360 Jiagu",
    "libsecexe": "Bangcle SecNeo",
    "libsecmain": "Bangcle SecNeo",
    "libdexhelper": "DexProtector",
    "libshell": "Tencent Legu",
    "libprotectclass": "Baidu protect",
    "libapptoolkit": "Ali packer",
    "libnesec": "NetEase packer",
    "libddog": "DDog packer",
    "libfakejni": "Ijiami",
    "libexec.so": "Ijiami",
    "libexecmain": "Ijiami",
}


def _parse_components(apk: object, facts: ApkFacts) -> None:
    """Walk the manifest tree for capabilities declared on components.

    ``<uses-permission android:name="...BIND_ACCESSIBILITY_SERVICE">`` is not
    how accessibility abuse is declared. Real malware binds the service:
    ``<service android:permission="...BIND_ACCESSIBILITY_SERVICE">`` with an
    intent filter. Reading only uses-permission missed every real sample.
    """

    try:
        root = apk.get_android_manifest_xml()  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("apk_component_walk_failed error=%s", type(exc).__name__)
        return
    if root is None:
        return

    declared: dict[str, bool] = {}
    for element in root.iter():
        tag = str(getattr(element, "tag", "") or "")
        attributes = getattr(element, "attrib", {}) or {}
        bind = attributes.get(f"{_ANDROID_NS}permission") or attributes.get("permission")
        if tag in {"service", "receiver", "activity"} and bind in _BIND_PERMISSIONS:
            declared[_BIND_PERMISSIONS[bind]] = True
        if tag == "action":
            name = attributes.get(f"{_ANDROID_NS}name") or attributes.get("name")
            capability = _INTENT_ACTIONS.get(str(name))
            if capability:
                declared[capability] = True
                if capability == "sms_receiver":
                    priority = _intent_filter_priority(element)
                    if priority is not None:
                        current = facts.sms_receiver_priority
                        facts.sms_receiver_priority = max(priority, current if current is not None else priority)
    facts.declared = declared


def _intent_filter_priority(action_element: object) -> int | None:
    parent = getattr(action_element, "getparent", lambda: None)()
    if parent is None:
        return None
    attributes = getattr(parent, "attrib", {}) or {}
    raw = attributes.get(f"{_ANDROID_NS}priority") or attributes.get("priority")
    return _as_int(raw)


def detect_packers(archive: zipfile.ZipFile) -> list[str]:
    """Name the packer when an APK carries a known packer's native library."""

    found: list[str] = []
    for info in archive.infolist()[:_MAX_ENTRIES]:
        lowered = info.filename.lower()
        if not (lowered.endswith(".so") or lowered.startswith("assets/")):
            continue
        base = lowered.rsplit("/", 1)[-1]
        for marker, name in _PACKER_MARKERS.items():
            if base.startswith(marker) or marker in base:
                if name not in found:
                    found.append(name)
    return found


def _clean(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text[:256] or None


def _as_int(value: object) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


# --- certificate -----------------------------------------------------------


def parse_certificate(data: bytes, archive: zipfile.ZipFile) -> ApkCertificate:
    """Extract the v1 signing certificate.

    The SHA-256 fingerprint is the strongest campaign-linking signal available
    statically: one fraud operation usually signs many repackaged apps with the
    same key.
    """

    certificate = ApkCertificate()
    der, schemes = _certificate_der(data, archive)
    certificate.schemes = schemes
    if der is None:
        return certificate

    certificate.sha256 = hashlib.sha256(der).hexdigest()
    try:
        from asn1crypto import x509

        parsed = x509.Certificate.load(der)
        subject = parsed.subject.human_friendly
        issuer = parsed.issuer.human_friendly
        certificate.subject = subject[:256]
        certificate.issuer = issuer[:256]
        certificate.self_signed = subject == issuer
        certificate.debug_certificate = any(
            marker in subject.casefold() for marker in _DEBUG_CERT_MARKERS
        )
        not_before = parsed["tbs_certificate"]["validity"]["not_before"].native
        not_after = parsed["tbs_certificate"]["validity"]["not_after"].native
        certificate.not_before = _as_utc(not_before)
        certificate.not_after = _as_utc(not_after)
        if certificate.not_before and certificate.not_after:
            certificate.validity_days = (certificate.not_after - certificate.not_before).days
    except Exception as exc:
        logger.warning("apk_certificate_parse_failed error=%s", type(exc).__name__)
    return certificate


def _certificate_der(data: bytes, archive: zipfile.ZipFile) -> tuple[bytes | None, list[str]]:
    """Return the signing certificate and which schemes signed the package.

    Order is v3 -> v2 -> v1: a package signed only with APK Signature Scheme
    v2 or v3 has no PKCS#7 block in META-INF, and reading v1 alone reported
    every modern app as unsigned (defect D9).
    """

    schemes: list[str] = []
    best: bytes | None = None
    try:
        from pyaxmlparser import APK

        apk = APK(data, raw=True)
        for scheme, getter in (
            ("v3", "get_certificates_der_v3"),
            ("v2", "get_certificates_der_v2"),
            ("v1", "get_certificates_der_v1"),
        ):
            method = getattr(apk, getter, None)
            if method is None:
                continue
            try:
                ders = [der for der in (method() or []) if der]
            except Exception:
                continue
            if ders:
                schemes.append(scheme)
                if best is None:
                    best = ders[0]
    except Exception:
        pass
    if best is not None:
        return best, schemes

    # Fall back to reading the PKCS#7 block straight out of META-INF.
    for info in archive.infolist():
        upper = info.filename.upper()
        if upper.startswith("META-INF/") and upper.endswith((".RSA", ".DSA", ".EC")):
            try:
                blob = archive.read(info)
            except (KeyError, zipfile.BadZipFile, RuntimeError):
                continue
            extracted = _der_from_pkcs7(blob)
            if extracted:
                return extracted, (schemes or ["v1"])
    return None, schemes


def _der_from_pkcs7(blob: bytes) -> bytes | None:
    try:
        from asn1crypto import cms

        content = cms.ContentInfo.load(blob)
        certificates = content["content"]["certificates"]
        for entry in certificates:
            return entry.chosen.dump()
    except Exception:
        return None
    return None


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


# --- embedded strings ------------------------------------------------------


def extract_strings(archive: zipfile.ZipFile) -> tuple[list[str], int]:
    """Pull printable strings from DEX, resources, and assets.

    Returns the strings and the DEX count. These feed the shared identifier
    extractor, so a C2 host or UPI ID baked into an app is linked exactly like
    one found in an SMS.
    """

    collected: list[str] = []
    seen: set[str] = set()
    scanned = 0
    dex_count = 0

    for info in archive.infolist():
        name = info.filename
        lowered = name.lower()
        is_dex = lowered.endswith(".dex")
        if is_dex:
            dex_count += 1
        interesting = (
            is_dex
            or lowered == "resources.arsc"
            or lowered.startswith("assets/")
            or lowered.startswith("res/raw/")
        )
        if not interesting or info.file_size == 0:
            continue
        if scanned >= _MAX_SCANNED_BYTES or len(collected) >= _MAX_STRINGS:
            break

        budget = min(info.file_size, _MAX_SCANNED_BYTES - scanned)
        try:
            with archive.open(info) as handle:
                blob = handle.read(budget)
        except (KeyError, zipfile.BadZipFile, RuntimeError, OSError):
            continue
        scanned += len(blob)

        # A DEX file has a real string table; reading it recovers non-ASCII
        # strings and avoids opcode noise. The ASCII scan still runs over it
        # as a fallback for packers that corrupt the table.
        if is_dex:
            for text in dex_strings(blob):
                if text in seen:
                    continue
                seen.add(text)
                collected.append(text)
                if len(collected) >= _MAX_STRINGS:
                    break

        for match in _ASCII_STRING_RE.finditer(blob):
            text = match.group(0).decode("ascii", "ignore").strip()
            if len(text) < 6 or text in seen:
                continue
            seen.add(text)
            collected.append(text)
            if len(collected) >= _MAX_STRINGS:
                break

    decoded = decode_base64_strings(collected)
    for text in decoded:
        if text not in seen:
            seen.add(text)
            collected.append(text)

    return collected, dex_count


def _uleb128(blob: bytes, offset: int) -> tuple[int, int]:
    """Read an unsigned LEB128 integer; returns (value, next_offset)."""

    result = 0
    shift = 0
    for _ in range(5):
        if offset >= len(blob):
            return result, offset
        byte = blob[offset]
        offset += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            break
        shift += 7
    return result, offset


def dex_strings(blob: bytes, limit: int = 40_000) -> list[str]:
    """Read a DEX file's string table properly.

    Walking ``header.string_ids_off`` and decoding each ``string_data_item``
    (a ULEB128 length followed by MUTF-8 bytes) is more precise than scanning
    for printable ASCII, and it recovers non-ASCII strings that the ASCII scan
    drops. The ASCII scan stays as the fallback for assets and resources.
    """

    if len(blob) < 112 or not blob.startswith(b"dex\n"):
        return []
    try:
        string_ids_size = int.from_bytes(blob[56:60], "little")
        string_ids_off = int.from_bytes(blob[60:64], "little")
    except Exception:
        return []
    if string_ids_size <= 0 or string_ids_off <= 0 or string_ids_off >= len(blob):
        return []

    out: list[str] = []
    count = min(string_ids_size, limit)
    end_of_table = string_ids_off + count * 4
    if end_of_table > len(blob):
        return []
    for index in range(count):
        pointer = int.from_bytes(blob[string_ids_off + index * 4: string_ids_off + index * 4 + 4], "little")
        if pointer <= 0 or pointer >= len(blob):
            continue
        length, cursor = _uleb128(blob, pointer)
        if length == 0 or length > 4_000:
            continue
        terminator = blob.find(b"\x00", cursor)
        if terminator < 0:
            continue
        raw = blob[cursor:terminator]
        if len(raw) > 4_000:
            continue
        try:
            text = raw.decode("utf-8", "replace").strip()
        except Exception:
            continue
        if len(text) >= 4:
            out.append(text)
    return out


_BASE64_CANDIDATE = re.compile(r"^[A-Za-z0-9+/]{16,}={0,2}$")


def decode_base64_strings(strings: list[str], limit: int = 500) -> list[str]:
    """Decode Base64-looking strings whose plaintext is printable.

    Scam apps hide endpoints and UPI IDs behind a single Base64 layer. The
    decoded text is tagged so an investigator knows it was not literal.
    """

    import base64
    import binascii

    decoded: list[str] = []
    for text in strings:
        if len(decoded) >= limit:
            break
        if not _BASE64_CANDIDATE.match(text) or len(text) % 4:
            continue
        try:
            raw = base64.b64decode(text, validate=True)
        except (binascii.Error, ValueError):
            continue
        if len(raw) < 6:
            continue
        try:
            plain = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if plain.isprintable() and any(char.isalnum() for char in plain):
            decoded.append(plain.strip())
    return decoded


# --- icon ------------------------------------------------------------------


def icon_dhash(data: bytes, archive: zipfile.ZipFile) -> str | None:
    """Perceptual difference-hash of the launcher icon.

    dHash is implemented directly on Pillow rather than pulling in imagehash,
    which requires scipy and numpy for a single function. Resizing to 9x8 and
    comparing horizontally adjacent pixels gives 64 bits that survive rescaling
    and recompression — enough to spot an app impersonating a bank's icon.
    """

    blob = _icon_bytes(data, archive)
    if blob is None:
        return None
    try:
        from PIL import Image

        with Image.open(io.BytesIO(blob)) as image:
            grayscale = image.convert("L").resize((9, 8), Image.Resampling.LANCZOS)
            pixels = list(grayscale.getdata())
    except Exception as exc:
        logger.warning("apk_icon_hash_failed error=%s", type(exc).__name__)
        return None

    bits = 0
    index = 0
    for row in range(8):
        offset = row * 9
        for column in range(8):
            if pixels[offset + column] > pixels[offset + column + 1]:
                bits |= 1 << index
            index += 1
    return f"{bits:016x}"


def _icon_bytes(data: bytes, archive: zipfile.ZipFile) -> bytes | None:
    candidates: list[str] = []
    try:
        from pyaxmlparser import APK

        apk = APK(data, raw=True)
        declared = apk.get_app_icon()
        if declared:
            candidates.append(str(declared))
    except Exception:
        pass

    names = [info.filename for info in archive.infolist()]
    candidates.extend(
        name
        for name in names
        if name.lower().startswith("res/")
        and name.lower().endswith(".png")
        and "ic_launcher" in name.lower()
    )

    for name in candidates:
        if name not in names:
            continue
        try:
            blob = archive.read(name)
        except (KeyError, zipfile.BadZipFile, RuntimeError):
            continue
        if blob:
            return blob
    return None


# --- entry point -----------------------------------------------------------


def inspect_apk(data: bytes) -> ApkFacts:
    """Run every static extraction step. Raises ApkParsingError on a bad container."""

    archive = validate_apk_container(data)
    facts = ApkFacts(size_bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    facts.entry_count = len(archive.infolist())

    parse_manifest(data, facts)
    facts.certificate = parse_certificate(data, archive)
    facts.extracted_strings, facts.dex_count = extract_strings(archive)
    facts.icon_dhash = icon_dhash(data, archive)
    facts.packers = detect_packers(archive)
    facts.split_names = [
        info.filename
        for info in archive.infolist()[:_MAX_ENTRIES]
        if info.filename.lower().endswith(".apk")
    ][:20]

    if facts.packers:
        facts.limitations.append(
            "The app is packed with "
            + ", ".join(facts.packers)
            + ". Packed code is unpacked at run time, so embedded URLs and identifiers "
            "are hidden from static inspection."
        )
    if facts.dex_count == 0:
        facts.limitations.append("No DEX bytecode was found, so embedded code strings were not available.")
    if not facts.extracted_strings:
        facts.limitations.append(
            "No readable strings were recovered. The app may be packed or encrypted, which hides "
            "embedded URLs and identifiers from static inspection."
        )
    facts.limitations.append(
        "Static inspection only: the app was not installed or executed, so run-time behaviour was not observed."
    )
    archive.close()
    return facts
