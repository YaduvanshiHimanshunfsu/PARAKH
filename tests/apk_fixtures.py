from __future__ import annotations

"""Build synthetic APKs for testing.

APK analysis cannot be tested without a real binary ``AndroidManifest.xml``,
and a hackathon machine has no Android SDK. Rather than committing a binary
sample of unknown provenance, this module *encodes* Android's binary XML
format directly, so every fixture is deterministic, inspectable, and safe.

Only the subset AAPT emits for a simple manifest is implemented: a string
pool, a resource map, and start/end element chunks.
"""

import io
import struct
import zipfile

# Chunk types from Android's ResourceTypes.h
_RES_XML_TYPE = 0x0003
_RES_STRING_POOL_TYPE = 0x0001
_RES_XML_RESOURCE_MAP_TYPE = 0x0180
_RES_XML_START_NAMESPACE_TYPE = 0x0100
_RES_XML_END_NAMESPACE_TYPE = 0x0101
_RES_XML_START_ELEMENT_TYPE = 0x0102
_RES_XML_END_ELEMENT_TYPE = 0x0103

_TYPE_STRING = 0x03
_TYPE_INT_DEC = 0x10

_ANDROID_NS = "http://schemas.android.com/apk/res/android"
_NO_ENTRY = 0xFFFFFFFF

# Framework attribute resource IDs. The resource map must list these in the
# same order as the matching attribute-name strings in the pool.
_ATTR_RESOURCE_IDS: dict[str, int] = {
    "label": 0x01010001,
    "icon": 0x01010002,
    "name": 0x01010003,
    "minSdkVersion": 0x0101020C,
    "versionCode": 0x0101021B,
    "versionName": 0x0101021C,
    "targetSdkVersion": 0x01010270,
}
_ATTR_ORDER = ["label", "icon", "name", "minSdkVersion", "versionCode", "versionName", "targetSdkVersion"]


class _StringPool:
    """Ordered, de-duplicated string table for the AXML string pool."""

    def __init__(self) -> None:
        self._items: list[str] = []
        self._index: dict[str, int] = {}
        # Attribute names must occupy the first slots so the resource map lines up.
        for name in _ATTR_ORDER:
            self.add(name)

    def add(self, value: str) -> int:
        if value not in self._index:
            self._index[value] = len(self._items)
            self._items.append(value)
        return self._index[value]

    def index(self, value: str) -> int:
        return self.add(value)

    def encode(self) -> bytes:
        offsets: list[int] = []
        body = bytearray()
        for item in self._items:
            offsets.append(len(body))
            encoded = item.encode("utf-16-le")
            body += struct.pack("<H", len(item))  # character count
            body += encoded
            body += b"\x00\x00"                   # UTF-16 terminator
        while len(body) % 4:
            body += b"\x00"

        header_size = 28
        strings_start = header_size + 4 * len(offsets)
        chunk_size = strings_start + len(body)

        chunk = bytearray()
        chunk += struct.pack("<HHI", _RES_STRING_POOL_TYPE, header_size, chunk_size)
        chunk += struct.pack("<I", len(self._items))  # stringCount
        chunk += struct.pack("<I", 0)                 # styleCount
        chunk += struct.pack("<I", 0)                 # flags: UTF-16, unsorted
        chunk += struct.pack("<I", strings_start)
        chunk += struct.pack("<I", 0)                 # stylesStart
        for offset in offsets:
            chunk += struct.pack("<I", offset)
        chunk += body
        return bytes(chunk)


def _resource_map_chunk() -> bytes:
    header_size = 8
    chunk_size = header_size + 4 * len(_ATTR_ORDER)
    chunk = struct.pack("<HHI", _RES_XML_RESOURCE_MAP_TYPE, header_size, chunk_size)
    for name in _ATTR_ORDER:
        chunk += struct.pack("<I", _ATTR_RESOURCE_IDS[name])
    return chunk


def _namespace_chunk(chunk_type: int, prefix: int, uri: int) -> bytes:
    return struct.pack(
        "<HHIIIII", chunk_type, 16, 24, 1, _NO_ENTRY, prefix, uri
    )


def _start_element(
    pool: _StringPool, name: str, attributes: list[tuple[str | None, str, object]]
) -> bytes:
    """Encode one start tag. Attributes are (namespace_uri, name, value)."""

    attribute_blob = bytearray()
    for namespace, attribute_name, value in attributes:
        ns_index = pool.index(namespace) if namespace else _NO_ENTRY
        name_index = pool.index(attribute_name)
        if isinstance(value, int):
            raw_index = _NO_ENTRY
            data_type = _TYPE_INT_DEC
            data = value
        else:
            raw_index = pool.index(str(value))
            data_type = _TYPE_STRING
            data = raw_index
        attribute_blob += struct.pack("<III", ns_index, name_index, raw_index)
        attribute_blob += struct.pack("<HBBI", 8, 0, data_type, data)

    header_size = 16
    chunk_size = header_size + 20 + len(attribute_blob)
    chunk = bytearray()
    chunk += struct.pack("<HHI", _RES_XML_START_ELEMENT_TYPE, header_size, chunk_size)
    chunk += struct.pack("<II", 1, _NO_ENTRY)          # lineNumber, comment
    chunk += struct.pack("<II", _NO_ENTRY, pool.index(name))
    chunk += struct.pack("<HHH", 20, 20, len(attributes))  # start, size, count
    chunk += struct.pack("<HHH", 0, 0, 0)                  # id/class/style index
    chunk += attribute_blob
    return bytes(chunk)


def _end_element(pool: _StringPool, name: str) -> bytes:
    return struct.pack(
        "<HHIIIII",
        _RES_XML_END_ELEMENT_TYPE,
        16,
        24,
        1,
        _NO_ENTRY,
        _NO_ENTRY,
        pool.index(name),
    )


def build_manifest(
    package: str = "com.example.app",
    *,
    label: str = "Example App",
    version_name: str = "1.0",
    version_code: int = 1,
    min_sdk: int = 21,
    target_sdk: int = 33,
    permissions: tuple[str, ...] = (),
) -> bytes:
    """Encode a binary AndroidManifest.xml that pyaxmlparser can decode."""

    pool = _StringPool()
    # Reserve the strings used structurally before any attribute values.
    pool.add(_ANDROID_NS)
    pool.add("android")
    for element in ("manifest", "uses-sdk", "uses-permission", "application", "activity"):
        pool.add(element)

    body = bytearray()
    body += _namespace_chunk(
        _RES_XML_START_NAMESPACE_TYPE, pool.index("android"), pool.index(_ANDROID_NS)
    )
    body += _start_element(
        pool,
        "manifest",
        [
            (None, "package", package),
            (_ANDROID_NS, "versionCode", version_code),
            (_ANDROID_NS, "versionName", version_name),
        ],
    )
    body += _start_element(
        pool,
        "uses-sdk",
        [
            (_ANDROID_NS, "minSdkVersion", min_sdk),
            (_ANDROID_NS, "targetSdkVersion", target_sdk),
        ],
    )
    body += _end_element(pool, "uses-sdk")
    for permission in permissions:
        body += _start_element(pool, "uses-permission", [(_ANDROID_NS, "name", permission)])
        body += _end_element(pool, "uses-permission")
    body += _start_element(pool, "application", [(_ANDROID_NS, "label", label)])
    body += _start_element(pool, "activity", [(_ANDROID_NS, "name", f"{package}.MainActivity")])
    body += _end_element(pool, "activity")
    body += _end_element(pool, "application")
    body += _end_element(pool, "manifest")
    body += _namespace_chunk(
        _RES_XML_END_NAMESPACE_TYPE, pool.index("android"), pool.index(_ANDROID_NS)
    )

    # The pool must be encoded last: element encoding adds strings to it.
    pool_chunk = pool.encode()
    resource_map = _resource_map_chunk()
    total = 8 + len(pool_chunk) + len(resource_map) + len(body)
    header = struct.pack("<HHI", _RES_XML_TYPE, 8, total)
    return header + pool_chunk + resource_map + bytes(body)


def build_apk(
    package: str = "com.example.app",
    *,
    label: str = "Example App",
    permissions: tuple[str, ...] = (),
    target_sdk: int = 33,
    dex_strings: tuple[str, ...] = (),
    include_manifest: bool = True,
    include_dex: bool = True,
    icon_png: bytes | None = None,
) -> bytes:
    """Assemble a synthetic but structurally valid APK."""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        if include_manifest:
            archive.writestr(
                "AndroidManifest.xml",
                build_manifest(
                    package, label=label, permissions=permissions, target_sdk=target_sdk
                ),
            )
        if include_dex:
            # Real DEX magic followed by padded printable strings, which is all
            # the string scanner reads.
            payload = b"dex\n035\x00" + b"\x00" * 56
            payload += b"\x00".join(s.encode("ascii", "ignore") for s in dex_strings)
            archive.writestr("classes.dex", payload)
        if icon_png is not None:
            archive.writestr("res/drawable/ic_launcher.png", icon_png)
        archive.writestr("resources.arsc", b"\x02\x00\x0c\x00" + b"\x00" * 32)
    return buffer.getvalue()


def build_png(seed: int = 0, size: int = 48) -> bytes:
    """Small patterned PNG for icon-hash tests.

    Deliberately not a solid colour: dHash compares adjacent pixels, so a flat
    image hashes to all zeros and could not distinguish two different icons.
    """

    from PIL import Image

    image = Image.new("RGB", (size, size))
    pixels = image.load()
    for x in range(size):
        for y in range(size):
            pixels[x, y] = (
                (x * 5 + seed * 37) % 256,
                (y * 3 + seed * 11) % 256,
                (x * y + seed) % 256,
            )
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def build_zip_bomb() -> bytes:
    """A small archive that expands enormously — must be rejected, not inspected."""

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("AndroidManifest.xml", build_manifest())
        archive.writestr("payload.bin", b"\x00" * 50_000_000)
    return buffer.getvalue()
