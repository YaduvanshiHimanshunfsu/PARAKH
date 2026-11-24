from __future__ import annotations

"""Checksum validators for identifier extraction (planversionalpha.md B.5).

Pure Python, no dependencies. These turn format-shaped guesses into
high-precision matches: a 34-character string starting with ``T`` is only a
TRON address if its Base58Check digest verifies, and a 15-digit run is only an
IMEI if it passes Luhn.

EIP-55 (Ethereum mixed-case checksum) is deliberately absent: it needs
Keccak-256, which is *not* ``hashlib.sha3_256``, and PARAKH does not add a
crypto dependency for one optional check.
"""

import hashlib

_B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_B58_INDEX = {char: index for index, char in enumerate(_B58_ALPHABET)}

_BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
_BECH32_CONST = 1
_BECH32M_CONST = 0x2BC830A3


def b58check_payload(value: str) -> bytes | None:
    """Decode a Base58Check string and verify its 4-byte double-SHA-256 tail."""

    if not value or any(char not in _B58_INDEX for char in value):
        return None
    number = 0
    for char in value:
        number = number * 58 + _B58_INDEX[char]
    raw = number.to_bytes((number.bit_length() + 7) // 8, "big") if number else b""
    # Each leading '1' encodes a leading zero byte.
    raw = b"\x00" * (len(value) - len(value.lstrip("1"))) + raw
    if len(raw) < 5:
        return None
    payload, checksum = raw[:-4], raw[-4:]
    if hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4] != checksum:
        return None
    return payload


def is_tron_address(value: str) -> bool:
    """TRON mainnet: 21-byte payload whose version byte is 0x41."""

    payload = b58check_payload(value)
    return bool(payload) and len(payload) == 21 and payload[0] == 0x41


def is_base58_bitcoin_address(value: str) -> bool:
    """Legacy P2PKH (0x00) or P2SH (0x05) Bitcoin address."""

    payload = b58check_payload(value)
    return bool(payload) and len(payload) == 21 and payload[0] in (0x00, 0x05)


def _bech32_polymod(values: list[int]) -> int:
    generator = (0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3)
    checksum = 1
    for value in values:
        top = checksum >> 25
        checksum = ((checksum & 0x1FFFFFF) << 5) ^ value
        for index in range(5):
            if (top >> index) & 1:
                checksum ^= generator[index]
    return checksum


def is_bech32_bitcoin_address(address: str) -> bool:
    """SegWit address with a valid bech32 (BIP-173) or bech32m (BIP-350) checksum."""

    lowered = address.lower()
    if lowered != address and address.upper() != address:
        return False  # mixed case is invalid in bech32
    hrp, separator, data = lowered.rpartition("1")
    if separator != "1" or hrp not in {"bc", "tb"} or len(data) < 6:
        return False
    try:
        values = [_BECH32_CHARSET.index(char) for char in data]
    except ValueError:
        return False
    expanded = [ord(char) >> 5 for char in hrp] + [0] + [ord(char) & 31 for char in hrp]
    return _bech32_polymod(expanded + values) in (_BECH32_CONST, _BECH32M_CONST)


def is_bitcoin_address(value: str) -> bool:
    return is_base58_bitcoin_address(value) or is_bech32_bitcoin_address(value)


def luhn_ok(digits: str) -> bool:
    """Luhn check digit, used for IMEI validation."""

    if not digits.isdigit() or len(digits) < 2:
        return False
    total = 0
    for index, char in enumerate(reversed(digits)):
        value = int(char)
        if index % 2:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


__all__ = [
    "b58check_payload",
    "is_tron_address",
    "is_base58_bitcoin_address",
    "is_bech32_bitcoin_address",
    "is_bitcoin_address",
    "luhn_ok",
]
