from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class IdentityRecord(Base):
    __tablename__ = "identities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(20))
    owner: Mapped[str] = mapped_column(String(120))
    purpose: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    allowed_actions: Mapped[str] = mapped_column(Text, default="[]")
    certificate_fingerprint: Mapped[str | None] = mapped_column(String(95), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    certificates: Mapped[list["CertificateRecord"]] = relationship(
        back_populates="identity", cascade="all, delete-orphan"
    )


class CertificateRecord(Base):
    __tablename__ = "certificates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    identity_id: Mapped[str] = mapped_column(ForeignKey("identities.id"), index=True)
    serial_number: Mapped[str] = mapped_column(String(128), index=True)
    subject: Mapped[str] = mapped_column(String(500))
    issuer: Mapped[str] = mapped_column(String(500))
    not_before: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    not_after: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    key_algorithm: Mapped[str] = mapped_column(String(80))
    fingerprint: Mapped[str] = mapped_column(String(95), unique=True)
    certificate_path: Mapped[str] = mapped_column(String(500))
    key_path: Mapped[str] = mapped_column(String(500))
    renewal_status: Mapped[str] = mapped_column(String(30), default="not_requested")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    identity: Mapped[IdentityRecord] = relationship(back_populates="certificates")


class ActionRequestRecord(Base):
    __tablename__ = "action_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    identity_id: Mapped[str] = mapped_column(ForeignKey("identities.id"), index=True)
    action: Mapped[str] = mapped_column(String(120))
    target: Mapped[str] = mapped_column(String(200))
    risk_level: Mapped[str] = mapped_column(String(20))
    approval_status: Mapped[str] = mapped_column(String(30))
    decision: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str] = mapped_column(String(500))
    result_payload: Mapped[str] = mapped_column(Text, default="{}")
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class IncidentRecord(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    identity_id: Mapped[str] = mapped_column(ForeignKey("identities.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    reason: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditEventRecord(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    actor: Mapped[str] = mapped_column(String(200))
    subject: Mapped[str] = mapped_column(String(200))
    result: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str] = mapped_column(String(500))
    correlation_id: Mapped[str] = mapped_column(String(36), index=True)
    incident_id: Mapped[str | None] = mapped_column(
        ForeignKey("incidents.id"), nullable=True, index=True
    )
    payload: Mapped[str] = mapped_column(Text, default="{}")
    previous_event_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_hash: Mapped[str] = mapped_column(String(64), unique=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


def safe_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    return payload or {}
