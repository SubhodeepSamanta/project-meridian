from __future__ import annotations

import json
from dataclasses import dataclass

from app.db.models import IdentityRecord


HIGH_RISK_ACTIONS = {
    "delete_data",
    "revoke_identity",
    "rotate_certificate",
    "rotate_trust_chain",
}
MEDIUM_RISK_ACTIONS = {"send_message", "update_configuration"}


@dataclass(frozen=True)
class PolicyDecision:
    risk_level: str
    approval_status: str
    decision: str
    reason: str


def risk_for_action(action: str) -> str:
    if action in HIGH_RISK_ACTIONS:
        return "high"
    if action in MEDIUM_RISK_ACTIONS:
        return "medium"
    return "low"


def evaluate_action(identity: IdentityRecord, action: str) -> PolicyDecision:
    risk_level = risk_for_action(action)
    if identity.status != "active":
        return PolicyDecision(
            risk_level=risk_level,
            approval_status="not_required",
            decision="deny",
            reason=f"identity status is {identity.status}",
        )

    allowed_actions = set(json.loads(identity.allowed_actions))
    if action not in allowed_actions:
        return PolicyDecision(
            risk_level=risk_level,
            approval_status="not_required",
            decision="deny",
            reason="action is not in the identity allow-list",
        )

    if risk_level == "high":
        return PolicyDecision(
            risk_level=risk_level,
            approval_status="pending",
            decision="approval_required",
            reason="high-risk action requires explicit operator approval",
        )

    return PolicyDecision(
        risk_level=risk_level,
        approval_status="not_required",
        decision="allow",
        reason="action is allowed by identity policy",
    )


def execute_simulated_action(action: str, target: str) -> dict[str, str | bool]:
    """Represent a safe deterministic target call without touching an external system."""
    return {
        "simulated": True,
        "action": action,
        "target": target,
        "outcome": "completed",
    }
