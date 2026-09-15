from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class IdentityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: Literal["service", "agent"]
    owner: str = Field(min_length=1, max_length=120)
    purpose: str = Field(min_length=1, max_length=500)
    allowed_actions: list[str] = Field(default_factory=list)


class CertificateIssueRequest(BaseModel):
    sans: list[str] = Field(default_factory=list)
    validity: str = "24h"


class ActionRequestCreate(BaseModel):
    action: str = Field(min_length=1, max_length=120)
    target: str = Field(min_length=1, max_length=200)
    certificate_fingerprint: str = Field(min_length=64, max_length=95)


class ActionRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    identity_id: str
    action: str
    target: str
    risk_level: str
    approval_status: str
    decision: str
    reason: str
    execution_result: dict
    requested_at: datetime


class IncidentCreate(BaseModel):
    identity_id: str
    reason: str = Field(min_length=1, max_length=500)


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    identity_id: str
    status: str
    reason: str
    created_at: datetime
    resolved_at: datetime | None


class IdentityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    kind: str
    owner: str
    purpose: str
    status: str
    allowed_actions: list[str]
    certificate_fingerprint: str | None
    created_at: datetime


class CertificateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    identity_id: str
    serial_number: str
    subject: str
    issuer: str
    not_before: datetime
    not_after: datetime
    status: str
    lifecycle_status: str
    key_algorithm: str
    fingerprint: str
    renewal_status: str
    created_at: datetime


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: str
    actor: str
    subject: str
    result: str
    reason: str
    correlation_id: str
    incident_id: str | None
    payload: dict
    previous_event_hash: str | None
    event_hash: str
    sequence: int
    timestamp: datetime
