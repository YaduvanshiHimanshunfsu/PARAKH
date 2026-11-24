from __future__ import annotations

"""ORM models for the investigation case store.

Written against the SQLAlchemy ORM only — no SQLite-specific SQL — so moving to
PostgreSQL is a connection-string change plus ``asyncpg`` (DECISIONS.md ADR-003).
"""

import secrets
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

_CASE_ID_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no look-alike characters


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_case_id() -> str:
    """Readable, collision-resistant public case reference (e.g. PRK-20261118-K7P2QX)."""

    suffix = "".join(secrets.choice(_CASE_ID_ALPHABET) for _ in range(6))
    return f"PRK-{utcnow():%Y%m%d}-{suffix}"


class Base(DeclarativeBase):
    pass


class UserRecord(Base):
    """An officer or admin. Citizens submit anonymously and have no account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(16), default="OFFICER")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    tokens: Mapped[list["AuthTokenRecord"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class AuthTokenRecord(Base):
    """Opaque bearer token. Only its hash is stored, never the token itself."""

    __tablename__ = "auth_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[UserRecord] = relationship(back_populates="tokens")


class CaseRecord(Base):
    """One analysed artifact, persisted for investigation."""

    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[str] = mapped_column(String(40), unique=True, index=True, default=new_case_id)

    artifact_type: Mapped[str] = mapped_column(String(16), index=True)
    risk_level: Mapped[str] = mapped_column(String(8), index=True)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    verdict: Mapped[str | None] = mapped_column(String(16), nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")

    status: Mapped[str] = mapped_column(String(16), default="NEW", index=True)
    source: Mapped[str] = mapped_column(String(16), default="OFFICER", index=True)

    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Exact-duplicate detection (normalised text) and near-duplicate detection.
    content_sha256: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    simhash: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)

    reporter_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    officer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)

    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    findings: Mapped[list["FindingRecord"]] = relationship(
        back_populates="case", cascade="all, delete-orphan", lazy="selectin"
    )
    identifiers: Mapped[list["IdentifierRecord"]] = relationship(
        back_populates="case", cascade="all, delete-orphan", lazy="selectin"
    )


class FindingRecord(Base):
    """One triggered indicator. Rows here are what make a risk score explainable."""

    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(64), index=True)
    severity: Mapped[str] = mapped_column(String(8))
    explanation: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)

    case: Mapped[CaseRecord] = relationship(back_populates="findings")


class IdentifierRecord(Base):
    """An actionable identifier tied to a case.

    The ``(type, value)`` index is what every cross-source link query and the
    heat-list aggregation depend on.
    """

    __tablename__ = "identifiers"
    __table_args__ = (
        Index("ix_identifier_type_value", "type", "value"),
        UniqueConstraint("case_id", "type", "value", name="uq_identifier_per_case"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(24))
    value: Mapped[str] = mapped_column(String(512))
    raw_value: Mapped[str] = mapped_column(String(512))
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[int] = mapped_column(Integer, default=100)
    # What this identifier is in the case: SUSPECT, VICTIM, IMPERSONATED_BRAND,
    # OFFICIAL_CONTACT or UNKNOWN (app/services/identifier_roles.py). Only
    # SUSPECT and UNKNOWN feed linking, campaigns and the heat-list, so a
    # bank's own helpline can no longer tie unrelated cases together.
    role: Mapped[str] = mapped_column(String(20), default="UNKNOWN", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    case: Mapped[CaseRecord] = relationship(back_populates="identifiers")


class BlacklistEntry(Base):
    """A reviewed known-bad identifier. Source is stored so a match is explainable."""

    __tablename__ = "blacklist_entries"
    __table_args__ = (
        UniqueConstraint("type", "value", name="uq_blacklist_entry"),
        Index("ix_blacklist_type_value", "type", "value"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(24))
    value: Mapped[str] = mapped_column(String(512))
    source: Mapped[str] = mapped_column(String(120))
    reason: Mapped[str] = mapped_column(Text, default="")
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DomainIntel(Base):
    """Cached RDAP result. Avoids repeat lookups and rate limits during a demo."""

    __tablename__ = "domain_intel"

    domain: Mapped[str] = mapped_column(String(253), primary_key=True)
    registrar: Mapped[str | None] = mapped_column(String(256), nullable=True)
    registered_on: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    age_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="UNKNOWN")
    nameservers: Mapped[dict] = mapped_column(JSON, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
