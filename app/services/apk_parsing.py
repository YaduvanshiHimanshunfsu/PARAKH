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
    except Exception as exc:
        logger.warning("apk_manifest_parse_failed error=%s", type(exc).__name__)
        facts.limitations.append(
            "The AndroidManifest could not be decoded. Package name, permissions and components "
            "are unavailable; this can indicate an obfuscated or deliberately malformed APK."
        )


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
    der = _certificate_der(data, archive)
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


def _certificate_der(data: bytes, archive: zipfile.ZipFile) -> bytes | None:
    try:
        from pyaxmlparser import APK

        apk = APK(data, raw=True)
        for der in apk.get_certificates_der_v1() if hasattr(apk, "get_certificates_der_v1") else []:
            if der:
                return der
    except Exception:
        pass

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
                return extracted
    return None


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

        for match in _ASCII_STRING_RE.finditer(blob):
            text = match.group(0).decode("ascii", "ignore").strip()
            if len(text) < 6 or text in seen:
                continue
            seen.add(text)
            collected.append(text)
            if len(collected) >= _MAX_STRINGS:
                break

    return collected, dex_count


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
