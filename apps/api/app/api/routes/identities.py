import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.db.models import CertificateRecord, IdentityRecord
from app.domain.audit.service import audit_service
from app.domain.identities.service import IdentityConflictError, register_identity
from app.schemas import IdentityCreate, IdentityResponse


router = APIRouter(prefix="/identities", tags=["identities"])


def to_identity_response(identity: IdentityRecord) -> IdentityResponse:
    return IdentityResponse(
        id=identity.id,
        name=identity.name,
        kind=identity.kind,
        owner=identity.owner,
        purpose=identity.purpose,
        status=identity.status,
        allowed_actions=json.loads(identity.allowed_actions),
        certificate_fingerprint=identity.certificate_fingerprint,
        created_at=identity.created_at,
    )


@router.post("", response_model=IdentityResponse, status_code=status.HTTP_201_CREATED)
def create_identity(
    payload: IdentityCreate,
    session: Session = Depends(get_session),
) -> IdentityResponse:
    try:
        identity = register_identity(
            session,
            audit_service,
            name=payload.name,
            kind=payload.kind,
            owner=payload.owner,
            purpose=payload.purpose,
            allowed_actions=payload.allowed_actions,
        )
    except IdentityConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return to_identity_response(identity)


@router.get("", response_model=list[IdentityResponse])
def list_identities(session: Session = Depends(get_session)) -> list[IdentityResponse]:
    identities = session.scalars(select(IdentityRecord).order_by(IdentityRecord.created_at)).all()
    return [to_identity_response(identity) for identity in identities]


@router.get("/{identity_id}")
def get_identity(identity_id: str, session: Session = Depends(get_session)) -> dict:
    identity = session.get(IdentityRecord, identity_id)
    if identity is None:
        raise HTTPException(status_code=404, detail="identity not found")
    certificates = session.scalars(
        select(CertificateRecord).where(CertificateRecord.identity_id == identity.id)
    ).all()
    return {
        "identity": to_identity_response(identity),
        "certificates": [
            {
                "id": certificate.id,
                "identity_id": certificate.identity_id,
                "serial_number": certificate.serial_number,
                "subject": certificate.subject,
                "issuer": certificate.issuer,
                "not_before": certificate.not_before,
                "not_after": certificate.not_after,
                "status": certificate.status,
                "key_algorithm": certificate.key_algorithm,
                "fingerprint": certificate.fingerprint,
                "renewal_status": certificate.renewal_status,
                "created_at": certificate.created_at,
            }
            for certificate in certificates
        ],
    }


@router.post("/{identity_id}/quarantine")
def quarantine_identity(
    identity_id: str,
    session: Session = Depends(get_session),
) -> dict:
    identity = session.get(IdentityRecord, identity_id)
    if identity is None:
        raise HTTPException(status_code=404, detail="identity not found")
    if identity.status == "revoked":
        raise HTTPException(status_code=409, detail="revoked identity cannot be quarantined")

    identity.status = "quarantined"
    audit_service.record(
        session,
        event_type="identity_quarantined",
        actor="operator",
        subject=identity.id,
        result="success",
        reason="identity isolated by operator",
    )
    session.commit()
    return {"identity": to_identity_response(identity)}
