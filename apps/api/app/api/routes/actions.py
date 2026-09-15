import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.db.models import ActionRequestRecord, IdentityRecord
from app.domain.audit.service import audit_service
from app.domain.policy.service import evaluate_action, execute_simulated_action, risk_for_action
from app.schemas import ActionRequestCreate, ActionRequestResponse


router = APIRouter(tags=["actions"])


def to_action_response(action_request: ActionRequestRecord) -> ActionRequestResponse:
    return ActionRequestResponse(
        id=action_request.id,
        identity_id=action_request.identity_id,
        action=action_request.action,
        target=action_request.target,
        risk_level=action_request.risk_level,
        approval_status=action_request.approval_status,
        decision=action_request.decision,
        reason=action_request.reason,
        execution_result=json.loads(action_request.result_payload),
        requested_at=action_request.requested_at,
    )


def _new_action_request(
    identity: IdentityRecord,
    payload: ActionRequestCreate,
    *,
    risk_level: str,
    approval_status: str,
    decision: str,
    reason: str,
) -> ActionRequestRecord:
    return ActionRequestRecord(
        id=str(uuid4()),
        identity_id=identity.id,
        action=payload.action,
        target=payload.target,
        risk_level=risk_level,
        approval_status=approval_status,
        decision=decision,
        reason=reason,
    )


@router.get("/actions", response_model=list[ActionRequestResponse])
def list_actions(session: Session = Depends(get_session)) -> list[ActionRequestResponse]:
    actions = session.scalars(
        select(ActionRequestRecord).order_by(ActionRequestRecord.requested_at)
    ).all()
    return [to_action_response(action_request) for action_request in actions]


@router.post(
    "/identities/{identity_id}/actions",
    response_model=ActionRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def request_action(
    identity_id: str,
    payload: ActionRequestCreate,
    session: Session = Depends(get_session),
) -> ActionRequestResponse:
    identity = session.get(IdentityRecord, identity_id)
    if identity is None:
        raise HTTPException(status_code=404, detail="identity not found")

    if identity.certificate_fingerprint != payload.certificate_fingerprint:
        action_request = _new_action_request(
            identity,
            payload,
            risk_level=risk_for_action(payload.action),
            approval_status="not_required",
            decision="deny",
            reason="presented certificate does not match the active identity",
        )
        session.add(action_request)
        audit_service.record(
            session,
            event_type="action_denied",
            actor=identity.name,
            subject=identity.id,
            result="failure",
            reason=action_request.reason,
            correlation_id=action_request.id,
            payload={"action": payload.action, "target": payload.target},
        )
        session.commit()
        return to_action_response(action_request)

    policy = evaluate_action(identity, payload.action)
    action_request = _new_action_request(
        identity,
        payload,
        risk_level=policy.risk_level,
        approval_status=policy.approval_status,
        decision=policy.decision,
        reason=policy.reason,
    )
    session.add(action_request)

    if policy.decision == "allow":
        action_request.result_payload = json.dumps(
            execute_simulated_action(payload.action, payload.target), sort_keys=True
        )
        audit_service.record(
            session,
            event_type="action_allowed",
            actor=identity.name,
            subject=identity.id,
            result="success",
            reason=policy.reason,
            correlation_id=action_request.id,
            payload={"action": payload.action, "target": payload.target},
        )
    elif policy.decision == "approval_required":
        audit_service.record(
            session,
            event_type="action_approval_required",
            actor=identity.name,
            subject=identity.id,
            result="pending",
            reason=policy.reason,
            correlation_id=action_request.id,
            payload={"action": payload.action, "target": payload.target},
        )
    else:
        audit_service.record(
            session,
            event_type="action_denied",
            actor=identity.name,
            subject=identity.id,
            result="failure",
            reason=policy.reason,
            correlation_id=action_request.id,
            payload={"action": payload.action, "target": payload.target},
        )

    session.commit()
    session.refresh(action_request)
    return to_action_response(action_request)


@router.post("/actions/{action_id}/approve", response_model=ActionRequestResponse)
def approve_action(
    action_id: str,
    session: Session = Depends(get_session),
) -> ActionRequestResponse:
    action_request = session.get(ActionRequestRecord, action_id)
    if action_request is None:
        raise HTTPException(status_code=404, detail="action request not found")
    if action_request.decision != "approval_required":
        raise HTTPException(status_code=409, detail="action request is not awaiting approval")

    identity = session.get(IdentityRecord, action_request.identity_id)
    if identity is None or identity.status != "active":
        action_request.approval_status = "denied"
        action_request.decision = "deny"
        action_request.reason = "identity is no longer active"
        audit_service.record(
            session,
            event_type="action_denied",
            actor="operator",
            subject=action_request.identity_id,
            result="failure",
            reason=action_request.reason,
            correlation_id=action_request.id,
        )
        session.commit()
        return to_action_response(action_request)

    action_request.approval_status = "approved"
    action_request.decision = "allow"
    action_request.reason = "high-risk action approved by operator"
    action_request.result_payload = json.dumps(
        execute_simulated_action(action_request.action, action_request.target), sort_keys=True
    )
    audit_service.record(
        session,
        event_type="action_approved",
        actor="operator",
        subject=identity.id,
        result="success",
        reason=action_request.reason,
        correlation_id=action_request.id,
        payload={"action": action_request.action, "target": action_request.target},
    )
    session.commit()
    session.refresh(action_request)
    return to_action_response(action_request)


@router.post("/actions/{action_id}/deny", response_model=ActionRequestResponse)
def deny_action(
    action_id: str,
    session: Session = Depends(get_session),
) -> ActionRequestResponse:
    action_request = session.get(ActionRequestRecord, action_id)
    if action_request is None:
        raise HTTPException(status_code=404, detail="action request not found")
    if action_request.decision != "approval_required":
        raise HTTPException(status_code=409, detail="action request is not awaiting approval")

    action_request.approval_status = "denied"
    action_request.decision = "deny"
    action_request.reason = "high-risk action denied by operator"
    audit_service.record(
        session,
        event_type="action_denied_by_operator",
        actor="operator",
        subject=action_request.identity_id,
        result="failure",
        reason=action_request.reason,
        correlation_id=action_request.id,
        payload={"action": action_request.action, "target": action_request.target},
    )
    session.commit()
    session.refresh(action_request)
    return to_action_response(action_request)
