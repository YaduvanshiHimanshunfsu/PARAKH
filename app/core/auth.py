from __future__ import annotations

"""Officer authentication for Investigation Mode.

Deliberately minimal: seeded accounts, opaque bearer tokens, no self-registration
and no password reset. Password hashing uses ``hashlib.scrypt`` from the standard
library rather than passlib/bcrypt — one less dependency, and no native-wheel
compatibility risk on Python 3.14.

Citizens are never authenticated; they submit anonymously.
"""

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.models import AuthTokenRecord, UserRecord
from app.db.session import get_session
from app.schemas import UserRole

logger = logging.getLogger(__name__)

# Roles that may use the investigation API at all. Fine-grained permission is
# decided per endpoint; this is only the door.
POLICE_ROLES = frozenset(
    {
        UserRole.OFFICER.value,
        UserRole.ADMIN.value,
        UserRole.OPERATOR.value,
        UserRole.IO.value,
        UserRole.STATION_HEAD.value,
        UserRole.SUPERVISOR.value,
        UserRole.STATE_VIEWER.value,
    }
)

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SALT_BYTES = 16
_TOKEN_BYTES = 32

bearer_scheme = HTTPBearer(auto_error=False)


# --- password hashing ------------------------------------------------------

def hash_password(password: str) -> str:
    """Return ``scrypt$<salt_hex>$<hash_hex>``."""

    salt = secrets.token_bytes(_SALT_BYTES)
    derived = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=32
    )
    return f"scrypt${salt.hex()}${derived.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time password check that never raises on malformed input."""

    try:
        algorithm, salt_hex, hash_hex = stored.split("$", 2)
        if algorithm != "scrypt":
            return False
        derived = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=_SCRYPT_N,
            r=_SCRYPT_R,
            p=_SCRYPT_P,
            dklen=32,
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(derived.hex(), hash_hex)


# --- tokens ----------------------------------------------------------------

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def issue_token(session: AsyncSession, user: UserRecord, ttl_hours: int) -> tuple[str, datetime]:
    """Create a bearer token. Only its SHA-256 hash is persisted."""

    token = secrets.token_urlsafe(_TOKEN_BYTES)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
    session.add(
        AuthTokenRecord(token_hash=_hash_token(token), user_id=user.id, expires_at=expires_at)
    )
    await session.flush()
    return token, expires_at


async def revoke_token(session: AsyncSession, token: str) -> None:
    await session.execute(
        delete(AuthTokenRecord).where(AuthTokenRecord.token_hash == _hash_token(token))
    )


async def resolve_user(session: AsyncSession, token: str) -> UserRecord | None:
    """Return the active user for a token, or None if invalid or expired."""

    record = (
        await session.execute(
            select(AuthTokenRecord).where(AuthTokenRecord.token_hash == _hash_token(token))
        )
    ).scalar_one_or_none()
    if record is None:
        return None

    expires_at = record.expires_at
    if expires_at.tzinfo is None:  # SQLite returns naive datetimes
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        await session.delete(record)
        return None

    user = (
        await session.execute(select(UserRecord).where(UserRecord.id == record.user_id))
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        return None
    return user


# --- dependencies ----------------------------------------------------------

async def require_officer(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> UserRecord:
    """Gate every /investigate/* route. Rejects anonymous and expired tokens."""

    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Officer authentication is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await resolve_user(session, credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is invalid or has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Every police role may reach the investigation API; what each one is
    # allowed to *do* is decided per endpoint by require_permission, and what
    # each one may *see* by jurisdiction scoping (app/core/permissions.py).
    if user.role == UserRole.CITIZEN.value or user.role not in POLICE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires an officer account.",
        )
    return user


# --- bootstrap -------------------------------------------------------------

async def ensure_bootstrap_officer(session: AsyncSession, settings: Settings) -> None:
    """Create the seeded officer account once, if configured.

    Does nothing when the credentials are unset, so a plain citizen-only
    deployment never gains an account it did not ask for.
    """

    username = (settings.officer_username or "").strip()
    secret = settings.officer_password.get_secret_value() if settings.officer_password else ""
    if not username or not secret:
        logger.info("officer_bootstrap_skipped reason=not_configured")
        return

    existing = (
        await session.execute(select(UserRecord).where(UserRecord.username == username))
    ).scalar_one_or_none()
    if existing is not None:
        return

    session.add(
        UserRecord(
            username=username,
            password_hash=hash_password(secret),
            role=UserRole.ADMIN.value,
        )
    )
    await session.flush()
    # Never log the password or its hash.
    logger.info("officer_bootstrap_created username=%s", username)


# --- account lockout (planversionalpha.md C.4) -----------------------------
#
# Counting failures per account, not only per IP: a password-spraying client
# rotates addresses, and a per-IP limit alone would let it through. The lock
# doubles on each further burst so a persistent attacker backs off quickly
# while a user who mistypes twice is barely inconvenienced.


def lock_remaining(user: "UserRecord") -> int:
    """Seconds left on this account's lock, or 0 if it is not locked."""

    locked_until = getattr(user, "locked_until", None)
    if locked_until is None:
        return 0
    if locked_until.tzinfo is None:  # SQLite returns naive datetimes
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    remaining = (locked_until - datetime.now(timezone.utc)).total_seconds()
    return int(remaining) if remaining > 0 else 0


def register_failure(user: "UserRecord", *, threshold: int, minutes: int, max_minutes: int) -> int:
    """Count a failed attempt and lock the account once the threshold is hit.

    Returns the lock duration applied in minutes, or 0 if none.
    """

    user.failed_logins = (user.failed_logins or 0) + 1
    if user.failed_logins < threshold:
        return 0
    # 1st lock = minutes, 2nd = 2x, 3rd = 4x, capped.
    bursts = (user.failed_logins - threshold) // max(1, threshold)
    duration = min(max_minutes, minutes * (2 ** bursts))
    user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=duration)
    return duration


def register_success(user: "UserRecord") -> None:
    user.failed_logins = 0
    user.locked_until = None


def mfa_required(role: str | None, configured: str) -> bool:
    roles = {item.strip().upper() for item in (configured or "").split(",") if item.strip()}
    return bool(role) and role.upper() in roles


def verify_totp(secret: str, code: str, *, window: int = 1) -> bool:
    """Verify a TOTP code (RFC 6238) if pyotp is installed.

    Returns False when the library is absent, so a deployment that has not
    installed it cannot accidentally accept any code.
    """

    if not secret or not code:
        return False
    try:
        import pyotp
    except ImportError:
        logger.warning("totp_unavailable: pyotp is not installed")
        return False
    try:
        return bool(pyotp.TOTP(secret).verify(code.strip(), valid_window=window))
    except Exception:
        return False
