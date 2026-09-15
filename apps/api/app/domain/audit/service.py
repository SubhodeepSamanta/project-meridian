from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import AuditEventRecord, safe_payload


@dataclass(frozen=True)
class AuditIntegrity:
    valid: bool
    event_count: int
    checked_through_sequence: int
    first_invalid_sequence: int | None = None
    error: str | None = None


def _event_material(
    *,
    event_id: str,
    event_type: str,
    actor: str,
    subject: str,
    result: str,
    reason: str,
    correlation_id: str,
    incident_id: str | None,
    payload: dict,
    previous_event_hash: str | None,
) -> dict:
    return {
        "id": event_id,
        "event_type": event_type,
        "actor": actor,
        "subject": subject,
        "result": result,
        "reason": reason,
        "correlation_id": correlation_id,
        "incident_id": incident_id,
        "payload": payload,
        "previous_event_hash": previous_event_hash,
    }


def _hash_material(material: dict) -> str:
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


class AuditService:
    def record(
        self,
        session: Session,
        *,
        event_type: str,
        actor: str,
        subject: str,
        result: str,
        reason: str,
        correlation_id: str | None = None,
        incident_id: str | None = None,
        payload: dict | None = None,
    ) -> AuditEventRecord:
        previous = session.scalar(
            select(AuditEventRecord).order_by(AuditEventRecord.sequence.desc()).limit(1)
        )
        last_sequence = session.scalar(select(func.max(AuditEventRecord.sequence))) or 0
        event_id = str(uuid4())
        event_payload = safe_payload(payload)
        event_correlation_id = correlation_id or event_id
        previous_event_hash = previous.event_hash if previous else None
        material = _event_material(
            event_id=event_id,
            event_type=event_type,
            actor=actor,
            subject=subject,
            result=result,
            reason=reason,
            correlation_id=event_correlation_id,
            incident_id=incident_id,
            payload=event_payload,
            previous_event_hash=previous_event_hash,
        )
        event_hash = _hash_material(material)
        event = AuditEventRecord(
            id=event_id,
            event_type=event_type,
            actor=actor,
            subject=subject,
            result=result,
            reason=reason,
            correlation_id=event_correlation_id,
            incident_id=incident_id,
            payload=json.dumps(event_payload, sort_keys=True),
            previous_event_hash=previous_event_hash,
            event_hash=event_hash,
            sequence=last_sequence + 1,
        )
        session.add(event)
        session.flush()
        return event

    def verify(self, session: Session) -> AuditIntegrity:
        events = session.scalars(
            select(AuditEventRecord).order_by(AuditEventRecord.sequence)
        ).all()
        previous_event_hash: str | None = None
        expected_sequence = 1

        for event in events:
            if event.sequence != expected_sequence:
                return AuditIntegrity(
                    valid=False,
                    event_count=len(events),
                    checked_through_sequence=expected_sequence - 1,
                    first_invalid_sequence=event.sequence,
                    error="audit sequence is not contiguous",
                )
            if event.previous_event_hash != previous_event_hash:
                return AuditIntegrity(
                    valid=False,
                    event_count=len(events),
                    checked_through_sequence=event.sequence - 1,
                    first_invalid_sequence=event.sequence,
                    error="audit hash link does not match the preceding event",
                )

            try:
                payload = json.loads(event.payload)
            except (TypeError, json.JSONDecodeError):
                return AuditIntegrity(
                    valid=False,
                    event_count=len(events),
                    checked_through_sequence=event.sequence - 1,
                    first_invalid_sequence=event.sequence,
                    error="audit payload is not valid JSON",
                )
            if not isinstance(payload, dict):
                return AuditIntegrity(
                    valid=False,
                    event_count=len(events),
                    checked_through_sequence=event.sequence - 1,
                    first_invalid_sequence=event.sequence,
                    error="audit payload is not an object",
                )

            expected_hash = _hash_material(
                _event_material(
                    event_id=event.id,
                    event_type=event.event_type,
                    actor=event.actor,
                    subject=event.subject,
                    result=event.result,
                    reason=event.reason,
                    correlation_id=event.correlation_id,
                    incident_id=event.incident_id,
                    payload=payload,
                    previous_event_hash=event.previous_event_hash,
                )
            )
            if event.event_hash != expected_hash:
                return AuditIntegrity(
                    valid=False,
                    event_count=len(events),
                    checked_through_sequence=event.sequence - 1,
                    first_invalid_sequence=event.sequence,
                    error="audit event hash does not match its contents",
                )

            previous_event_hash = event.event_hash
            expected_sequence += 1

        return AuditIntegrity(
            valid=True,
            event_count=len(events),
            checked_through_sequence=len(events),
        )


audit_service = AuditService()
