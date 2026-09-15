from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from uuid import uuid4

from app.api.dependencies import get_session
from app.db.models import CertificateRecord, IdentityRecord
from app.domain.audit.service import audit_service
from app.integrations.step_ca import StepCaError
from app.schemas import CertificateIssueRequest, CertificateResponse


router = APIRouter(tags=["certificates"])


def to_certificate_response(certificate: CertificateRecord) -> CertificateResponse:
    return CertificateResponse(
        id=certificate.id,
        identity_id=certificate.identity_id,
        serial_number=certificate.serial_number,
        subject=certificate.subject,
        issuer=certificate.issuer,
        not_before=certificate.not_before,
        not_after=certificate.not_after,
        status=certificate.status,
        lifecycle_status=certificate_lifecycle_status(certificate),
        key_algorithm=certificate.key_algorithm,
        fingerprint=certificate.fingerprint,
        renewal_status=certificate.renewal_status,
        created_at=certificate.created_at,
    )


def certificate_lifecycle_status(certificate: CertificateRecord) -> str:
    if certificate.status in {"revoked", "retired"}:
        return certificate.status
    now = datetime.now(timezone.utc)
    not_after = certificate.not_after
    if not_after.tzinfo is None:
        not_after = not_after.replace(tzinfo=timezone.utc)
    if not_after <= now:
        return "expired"
    if not_after <= now + timedelta(hours=6):
        return "expiring_soon"
    return "active"


def retire_active_certificates(
    session: Session,
    identity_id: str,
    *,
    reason: str,
) -> None:
    active_certificates = session.scalars(
        select(CertificateRecord)
        .where(
            CertificateRecord.identity_id == identity_id,
            CertificateRecord.status == "active",
        )
        .order_by(CertificateRecord.created_at)
    ).all()
    for previous in active_certificates:
        previous.status = "retired"
        audit_service.record(
            session,
            event_type="certificate_retired",
            actor="operator",
            subject=identity_id,
            result="success",
            reason=reason,
            payload={"certificate_id": previous.id, "fingerprint": previous.fingerprint},
        )


@router.get("/certificates", response_model=list[CertificateResponse])
def list_certificates(session: Session = Depends(get_session)) -> list[CertificateResponse]:
    certificates = session.scalars(
        select(CertificateRecord).order_by(CertificateRecord.created_at)
    ).all()
    return [to_certificate_response(certificate) for certificate in certificates]


@router.get("/certificates/expiring", response_model=list[CertificateResponse])
def list_expiring_certificates(
    session: Session = Depends(get_session),
) -> list[CertificateResponse]:
    certificates = session.scalars(
        select(CertificateRecord).where(CertificateRecord.status == "active").order_by(
            CertificateRecord.not_after
        )
    ).all()
    return [
        to_certificate_response(certificate)
        for certificate in certificates
        if certificate_lifecycle_status(certificate) in {"expiring_soon", "expired"}
    ]


@router.post(
    "/identities/{identity_id}/certificates",
    response_model=CertificateResponse,
    status_code=status.HTTP_201_CREATED,
)
def issue_certificate(
    identity_id: str,
    payload: CertificateIssueRequest,
    request: Request,
    session: Session = Depends(get_session),
) -> CertificateResponse:
    identity = session.get(IdentityRecord, identity_id)
    if identity is None:
        raise HTTPException(status_code=404, detail="identity not found")
    if identity.status != "active":
        raise HTTPException(status_code=409, detail="identity is not eligible for certificate issuance")

    sans = payload.sans or [identity.name]
    try:
        issued = request.app.state.step_ca.issue_certificate(
            identity.name,
            sans,
            payload.validity,
        )
    except StepCaError as error:
        audit_service.record(
            session,
            event_type="certificate_issue_failed",
            actor="operator",
            subject=identity.id,
            result="failure",
            reason="certificate authority rejected the request",
            payload={"error": str(error)[:200]},
        )
        session.commit()
        raise HTTPException(status_code=502, detail="certificate issuance failed") from error

    certificate = CertificateRecord(
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
    retire_active_certificates(
        session,
        identity.id,
        reason="previous active certificate retired when a new certificate was issued",
    )
    session.add(certificate)
    identity.certificate_fingerprint = issued.fingerprint
    audit_service.record(
        session,
        event_type="certificate_issued",
        actor="operator",
        subject=identity.id,
        result="success",
        reason="certificate issued by configured step-ca authority",
        payload={
            "certificate_id": certificate.id,
            "serial_number": issued.serial_number,
            "fingerprint": issued.fingerprint,
        },
    )
    session.commit()
    session.refresh(certificate)
    return to_certificate_response(certificate)


@router.post("/certificates/{certificate_id}/revoke")
def revoke_certificate(
    certificate_id: str,
    request: Request,
    session: Session = Depends(get_session),
) -> dict:
    certificate = session.get(CertificateRecord, certificate_id)
    if certificate is None:
        raise HTTPException(status_code=404, detail="certificate not found")
    if certificate.status == "revoked":
        return {"certificate": to_certificate_response(certificate)}

    try:
        request.app.state.step_ca.revoke_certificate(certificate.serial_number)
    except StepCaError as error:
        audit_service.record(
            session,
            event_type="certificate_revoke_failed",
            actor="operator",
            subject=certificate.identity_id,
            result="failure",
            reason="certificate authority rejected the revocation request",
            payload={"certificate_id": certificate.id, "error": str(error)[:200]},
        )
        session.commit()
        raise HTTPException(status_code=502, detail="certificate revocation failed") from error

    identity = session.get(IdentityRecord, certificate.identity_id)
    certificate.status = "revoked"
    if identity is not None and identity.certificate_fingerprint == certificate.fingerprint:
        identity.status = "revoked"
    audit_service.record(
        session,
        event_type="certificate_revoked",
        actor="operator",
        subject=certificate.identity_id,
        result="success",
        reason="certificate revoked by operator",
        payload={"certificate_id": certificate.id, "serial_number": certificate.serial_number},
    )
    session.commit()
    return {"certificate": to_certificate_response(certificate)}


@router.post("/certificates/{certificate_id}/renew")
def renew_certificate(
    certificate_id: str,
    request: Request,
    session: Session = Depends(get_session),
) -> dict:
    certificate = session.get(CertificateRecord, certificate_id)
    if certificate is None:
        raise HTTPException(status_code=404, detail="certificate not found")
    if certificate.status in {"revoked", "retired"}:
        raise HTTPException(status_code=409, detail="certificate cannot be renewed")

    identity = session.get(IdentityRecord, certificate.identity_id)
    if identity is None:
        raise HTTPException(status_code=404, detail="identity not found")
    if identity.status != "active":
        raise HTTPException(status_code=409, detail="identity is not eligible for renewal")

    try:
        issued = request.app.state.step_ca.issue_certificate(identity.name, [identity.name], "24h")
    except StepCaError as error:
        audit_service.record(
            session,
            event_type="certificate_renewal_failed",
            actor="operator",
            subject=identity.id,
            result="failure",
            reason="certificate authority rejected the renewal request",
            payload={"certificate_id": certificate.id, "error": str(error)[:200]},
        )
        session.commit()
        raise HTTPException(status_code=502, detail="certificate renewal failed") from error

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
    retire_active_certificates(
        session,
        identity.id,
        reason="previous active certificate retired during renewal",
    )
    identity.certificate_fingerprint = issued.fingerprint
    session.add(replacement)
    audit_service.record(
        session,
        event_type="certificate_renewed",
        actor="operator",
        subject=identity.id,
        result="success",
        reason="certificate renewed before lifecycle end",
        payload={
            "previous_certificate_id": certificate.id,
            "replacement_certificate_id": replacement.id,
            "fingerprint": issued.fingerprint,
        },
    )
    session.commit()
    session.refresh(replacement)
    return {
        "previous_certificate": to_certificate_response(certificate),
        "certificate": to_certificate_response(replacement),
    }
