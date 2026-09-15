from __future__ import annotations

import hashlib
import json
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import AuditEventRecord, safe_payload


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
        material = {
            "id": event_id,
            "event_type": event_type,
            "actor": actor,
            "subject": subject,
            "result": result,
            "reason": reason,
            "correlation_id": correlation_id or event_id,
            "incident_id": incident_id,
            "payload": event_payload,
            "previous_event_hash": previous.event_hash if previous else None,
        }
        event_hash = hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        event = AuditEventRecord(
            id=event_id,
            event_type=event_type,
            actor=actor,
            subject=subject,
            result=result,
            reason=reason,
            correlation_id=correlation_id or event_id,
            incident_id=incident_id,
            payload=json.dumps(event_payload, sort_keys=True),
            previous_event_hash=previous.event_hash if previous else None,
            event_hash=event_hash,
            sequence=last_sequence + 1,
        )
        session.add(event)
        session.flush()
        return event


audit_service = AuditService()
