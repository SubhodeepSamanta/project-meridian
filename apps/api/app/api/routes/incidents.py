from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.api.routes.certificates import to_certificate_response
from app.api.routes.identities import to_identity_response
from app.db.models import CertificateRecord, IdentityRecord, IncidentRecord
from app.domain.audit.service import audit_service
from app.integrations.step_ca import StepCaError
from app.schemas import IncidentCreate, IncidentResponse


router = APIRouter(prefix="/incidents", tags=["incidents"])


def to_incident_response(incident: IncidentRecord) -> IncidentResponse:
    return IncidentResponse(
        id=incident.id,
        identity_id=incident.identity_id,
        status=incident.status,
        reason=incident.reason,
        created_at=incident.created_at,
        resolved_at=incident.resolved_at,
    )


@router.get("", response_model=list[IncidentResponse])
def list_incidents(session: Session = Depends(get_session)) -> list[IncidentResponse]:
    incidents = session.scalars(
        select(IncidentRecord).order_by(IncidentRecord.created_at)
    ).all()
    return [to_incident_response(incident) for incident in incidents]


@router.post("/compromise", response_model=IncidentResponse, status_code=201)
def open_compromise_incident(
    payload: IncidentCreate,
    request: Request,
    session: Session = Depends(get_session),
) -> IncidentResponse:
    identity = session.get(IdentityRecord, payload.identity_id)
    if identity is None:
        raise HTTPException(status_code=404, detail="identity not found")
    if identity.status != "active":
        raise HTTPException(status_code=409, detail="only an active identity can open a compromise incident")

    incident = IncidentRecord(
        id=str(uuid4()),
        identity_id=identity.id,
        status="open",
        reason=payload.reason,
    )
    session.add(incident)
    identity.status = "quarantined"
    audit_service.record(
        session,
        event_type="incident_opened",
        actor="operator",
        subject=identity.id,
        result="success",
        reason=payload.reason,
        incident_id=incident.id,
        payload={"identity_id": identity.id},
    )
    audit_service.record(
        session,
        event_type="identity_quarantined",
        actor="operator",
        subject=identity.id,
        result="success",
        reason="identity quarantined during compromise response",
        incident_id=incident.id,
    )

    active_certificates = session.scalars(
        select(CertificateRecord).where(
            CertificateRecord.identity_id == identity.id,
            CertificateRecord.status == "active",
        )
    ).all()
    for certificate in active_certificates:
        try:
            request.app.state.step_ca.revoke_certificate(certificate.serial_number)
        except StepCaError as error:
            audit_service.record(
                session,
                event_type="certificate_revoke_failed",
                actor="operator",
                subject=identity.id,
                result="failure",
                reason="certificate authority rejected compromise revocation",
                incident_id=incident.id,
                payload={"certificate_id": certificate.id, "error": str(error)[:200]},
            )
            session.commit()
            raise HTTPException(status_code=502, detail="compromise containment failed") from error
        certificate.status = "revoked"
        audit_service.record(
            session,
            event_type="certificate_revoked",
            actor="operator",
            subject=identity.id,
            result="success",
            reason="certificate revoked during compromise response",
            incident_id=incident.id,
            payload={"certificate_id": certificate.id, "serial_number": certificate.serial_number},
        )

    session.commit()
    session.refresh(incident)
    return to_incident_response(incident)


@router.post("/{incident_id}/recover")
def recover_incident(
    incident_id: str,
    request: Request,
    session: Session = Depends(get_session),
) -> dict:
    incident = session.get(IncidentRecord, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="incident not found")
    if incident.status != "open":
        raise HTTPException(status_code=409, detail="incident is not open")

    identity = session.get(IdentityRecord, incident.identity_id)
    if identity is None:
        raise HTTPException(status_code=404, detail="identity not found")
    if identity.status != "quarantined":
        raise HTTPException(status_code=409, detail="identity is not quarantined")

    try:
        issued = request.app.state.step_ca.issue_certificate(identity.name, [identity.name], "24h")
    except StepCaError as error:
        audit_service.record(
            session,
            event_type="recovery_failed",
            actor="operator",
            subject=identity.id,
            result="failure",
            reason="certificate replacement could not be issued",
            incident_id=incident.id,
            payload={"error": str(error)[:200]},
        )
        session.commit()
        raise HTTPException(status_code=502, detail="identity recovery failed") from error

    replacement = CertificateRecord(
        id=str(uuid4()),
        identity_id=identity.id,
        serial_number=issued.serial_number,
        subject=issued.subject,
        issuer=issued.issuer,
        not_before=issued.not_before,
        not_after=issued.not_after,
        status="active",
        key_algorithm=issued.key_algorithm,
        fingerprint=issued.fingerprint,
        certificate_path=issued.certificate_path,
        key_path=issued.key_path,
    )
    identity.status = "active"
    identity.certificate_fingerprint = issued.fingerprint
    incident.status = "resolved"
    incident.resolved_at = datetime.now(timezone.utc)
    session.add(replacement)
    audit_service.record(
        session,
        event_type="certificate_replaced",
        actor="operator",
        subject=identity.id,
        result="success",
        reason="replacement certificate issued during recovery",
        incident_id=incident.id,
        payload={"replacement_certificate_id": replacement.id},
    )
    audit_service.record(
        session,
        event_type="recovery_completed",
        actor="operator",
        subject=identity.id,
        result="success",
        reason="identity recovered after certificate replacement",
        incident_id=incident.id,
        payload={"replacement_certificate_id": replacement.id},
    )
    session.commit()
    session.refresh(replacement)
    session.refresh(incident)
    return {
        "incident": to_incident_response(incident),
        "identity": to_identity_response(identity),
        "certificate": to_certificate_response(replacement),
    }
