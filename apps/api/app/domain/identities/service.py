import json
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import IdentityRecord
from app.domain.audit.service import AuditService


class IdentityConflictError(RuntimeError):
    pass


def register_identity(
    session: Session,
    audit: AuditService,
    *,
    name: str,
    kind: str,
    owner: str,
    purpose: str,
    allowed_actions: list[str],
    actor: str = "operator",
) -> IdentityRecord:
    if session.scalar(select(IdentityRecord).where(IdentityRecord.name == name)):
        raise IdentityConflictError(f"identity name already exists: {name}")

    identity = IdentityRecord(
        id=str(uuid4()),
        name=name,
        kind=kind,
        owner=owner,
        purpose=purpose,
        allowed_actions=json.dumps(sorted(set(allowed_actions))),
    )
    session.add(identity)
    audit.record(
        session,
        event_type="identity_registered",
        actor=actor,
        subject=identity.id,
        result="success",
        reason="identity registered",
        payload={"name": name, "kind": kind},
    )
    session.commit()
    session.refresh(identity)
    return identity
