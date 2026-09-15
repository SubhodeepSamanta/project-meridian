import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.db.models import AuditEventRecord
from app.schemas import AuditEventResponse


router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/events", response_model=list[AuditEventResponse])
def list_events(session: Session = Depends(get_session)) -> list[AuditEventResponse]:
    events = session.scalars(
        select(AuditEventRecord).order_by(AuditEventRecord.sequence)
    ).all()
    return [
        AuditEventResponse(
            id=event.id,
            event_type=event.event_type,
            actor=event.actor,
            subject=event.subject,
            result=event.result,
            reason=event.reason,
            correlation_id=event.correlation_id,
            incident_id=event.incident_id,
            payload=json.loads(event.payload),
            previous_event_hash=event.previous_event_hash,
            event_hash=event.event_hash,
            sequence=event.sequence,
            timestamp=event.timestamp,
        )
        for event in events
    ]
