from datetime import datetime, timedelta, timezone
from subprocess import CompletedProcess, TimeoutExpired

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.db.models import AuditEventRecord
from app.integrations.step_ca import IssuedCertificate, StepCaError
from app.integrations.step_ca import StepCaClient
from app.main import create_app


class FakeStepCaClient:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.issue_count = 0

    def health(self) -> bool:
        return True

    def issue_certificate(
        self,
        subject: str,
        sans: list[str],
        validity: str,
    ) -> IssuedCertificate:
        if self.should_fail:
            raise StepCaError("simulated CA failure")
        self.issue_count += 1
        now = datetime.now(timezone.utc)
        serial_number = "ABC123" if self.issue_count == 1 else f"ABC{self.issue_count:06d}"
        fingerprint = "a" * 64 if self.issue_count == 1 else f"{self.issue_count:064x}"
        return IssuedCertificate(
            certificate_path="/ignored/certificate.crt",
            key_path="/ignored/private.key",
            serial_number=serial_number,
            subject=f"CN={subject}",
            issuer="CN=Meridian Intermediate CA",
            not_before=now,
            not_after=now + timedelta(hours=24),
            key_algorithm="EllipticCurvePublicKey",
            fingerprint=fingerprint,
        )

    def revoke_certificate(self, serial_number: str) -> None:
        return None


def make_client(step_ca: FakeStepCaClient | None = None) -> TestClient:
    app = create_app(
        Settings(
            database_url="sqlite+pysqlite:///:memory:",
            hsm_ca_url="",
            hsm_ca_root="",
        ),
        step_ca_client=step_ca or FakeStepCaClient(),
    )
    return TestClient(app)


def create_identity(client: TestClient) -> dict:
    response = client.post(
        "/identities",
        json={
            "name": "agent-alpha",
            "kind": "agent",
            "owner": "meridian-lab",
            "purpose": "deterministic test actions",
            "allowed_actions": ["read_status"],
        },
    )
    assert response.status_code == 201
    return response.json()


def issue_identity_certificate(client: TestClient, identity: dict) -> dict:
    response = client.post(
        f"/identities/{identity['id']}/certificates",
        json={"sans": [identity["name"]], "validity": "24h"},
    )
    assert response.status_code == 201
    return response.json()


def test_identity_registration_creates_audit_event() -> None:
    with make_client() as client:
        identity = create_identity(client)
        assert identity["status"] == "active"
        assert identity["allowed_actions"] == ["read_status"]

        events = client.get("/audit/events").json()
        assert [event["event_type"] for event in events] == ["identity_registered"]
        assert [event["sequence"] for event in events] == [1]
        assert events[0]["previous_event_hash"] is None
        assert events[0]["event_hash"]


def test_protected_boundary_is_explicit_when_not_configured() -> None:
    with make_client() as client:
        response = client.get("/protected-boundary")

        assert response.status_code == 200
        assert response.json() == {
            "status": "unavailable",
            "token_label": "meridian-hsm",
            "key_store": "PKCS#11 / SoftHSM2",
            "key_objects": ["meridian-hsm-root", "meridian-hsm-intermediate"],
            "api_disk_key_access": "not mounted",
            "ca_endpoint": "not configured",
        }


def test_certificate_issuance_returns_metadata_without_private_key() -> None:
    with make_client() as client:
        identity = create_identity(client)
        response = client.post(
            f"/identities/{identity['id']}/certificates",
            json={"sans": ["agent-alpha"], "validity": "24h"},
        )

        assert response.status_code == 201
        body = response.json()
        assert body["fingerprint"] == "a" * 64
        assert body["lifecycle_status"] == "active"
        assert "key_path" not in body
        assert "private_key" not in body

        events = client.get("/audit/events").json()
        assert [event["event_type"] for event in events] == [
            "identity_registered",
            "certificate_issued",
        ]
        assert [event["sequence"] for event in events] == [1, 2]


def test_certificate_issue_validates_duration_and_fingerprint_shape() -> None:
    with make_client() as client:
        identity = create_identity(client)
        invalid_duration = client.post(
            f"/identities/{identity['id']}/certificates",
            json={"validity": "--not-a-duration"},
        )
        assert invalid_duration.status_code == 422

        invalid_fingerprint = client.post(
            f"/identities/{identity['id']}/actions",
            json={
                "action": "read_status",
                "target": "service-a",
                "certificate_fingerprint": "not-a-sha256-fingerprint",
            },
        )
        assert invalid_fingerprint.status_code == 422


def test_certificate_failure_creates_failure_audit_event() -> None:
    with make_client(FakeStepCaClient(should_fail=True)) as client:
        identity = create_identity(client)
        response = client.post(f"/identities/{identity['id']}/certificates", json={})

        assert response.status_code == 502
        assert response.json()["detail"] == "certificate issuance failed"
        events = client.get("/audit/events").json()
        assert events[-1]["event_type"] == "certificate_issue_failed"
        assert events[-1]["result"] == "failure"


def test_quarantine_changes_state_and_creates_audit_event() -> None:
    with make_client() as client:
        identity = create_identity(client)
        response = client.post(f"/identities/{identity['id']}/quarantine")

        assert response.status_code == 200
        assert response.json()["identity"]["status"] == "quarantined"
        events = client.get("/audit/events").json()
        assert events[-1]["event_type"] == "identity_quarantined"


def test_allowed_action_is_executed_and_audited() -> None:
    with make_client() as client:
        identity = create_identity(client)
        certificate = issue_identity_certificate(client, identity)
        response = client.post(
            f"/identities/{identity['id']}/actions",
            json={
                "action": "read_status",
                "target": "service-a",
                "certificate_fingerprint": certificate["fingerprint"],
            },
        )

        assert response.status_code == 201
        body = response.json()
        assert body["decision"] == "allow"
        assert body["execution_result"]["outcome"] == "completed"
        assert client.get("/audit/events").json()[-1]["event_type"] == "action_allowed"


def test_unauthorized_action_is_denied_and_audited() -> None:
    with make_client() as client:
        identity = create_identity(client)
        certificate = issue_identity_certificate(client, identity)
        response = client.post(
            f"/identities/{identity['id']}/actions",
            json={
                "action": "delete_data",
                "target": "service-a",
                "certificate_fingerprint": certificate["fingerprint"],
            },
        )

        assert response.status_code == 201
        assert response.json()["decision"] == "deny"
        assert client.get("/audit/events").json()[-1]["event_type"] == "action_denied"


def test_high_risk_action_waits_for_and_accepts_operator_approval() -> None:
    with make_client() as client:
        response = client.post(
            "/identities",
            json={
                "name": "agent-approval",
                "kind": "agent",
                "owner": "meridian-lab",
                "purpose": "approval workflow test",
                "allowed_actions": ["rotate_certificate"],
            },
        )
        assert response.status_code == 201
        identity = response.json()
        certificate = issue_identity_certificate(client, identity)

        pending = client.post(
            f"/identities/{identity['id']}/actions",
            json={
                "action": "rotate_certificate",
                "target": "agent-approval",
                "certificate_fingerprint": certificate["fingerprint"],
            },
        )
        assert pending.status_code == 201
        assert pending.json()["decision"] == "approval_required"
        assert pending.json()["approval_status"] == "pending"

        approved = client.post(f"/actions/{pending.json()['id']}/approve")
        assert approved.status_code == 200
        assert approved.json()["decision"] == "allow"
        assert approved.json()["approval_status"] == "approved"
        assert approved.json()["execution_result"]["simulated"] is True

        event_types = [event["event_type"] for event in client.get("/audit/events").json()]
        assert "action_approval_required" in event_types
        assert "action_approved" in event_types


def test_certificate_renewal_retires_old_certificate() -> None:
    with make_client() as client:
        identity = create_identity(client)
        certificate = issue_identity_certificate(client, identity)
        response = client.post(f"/certificates/{certificate['id']}/renew")

        assert response.status_code == 200
        body = response.json()
        assert body["previous_certificate"]["status"] == "retired"
        assert body["certificate"]["status"] == "active"
        assert body["certificate"]["fingerprint"] != certificate["fingerprint"]
        assert client.get("/audit/events").json()[-1]["event_type"] == "certificate_renewed"


def test_reissuing_certificate_retires_previous_active_credential() -> None:
    with make_client() as client:
        identity = create_identity(client)
        first = issue_identity_certificate(client, identity)
        second = issue_identity_certificate(client, identity)

        detail = client.get(f"/identities/{identity['id']}").json()
        certificates = {item["fingerprint"]: item for item in detail["certificates"]}
        assert certificates[first["fingerprint"]]["status"] == "retired"
        assert certificates[second["fingerprint"]]["status"] == "active"
        assert detail["identity"]["certificate_fingerprint"] == second["fingerprint"]


def test_revoking_retired_certificate_does_not_revoke_current_identity() -> None:
    with make_client() as client:
        identity = create_identity(client)
        first = issue_identity_certificate(client, identity)
        second = issue_identity_certificate(client, identity)

        response = client.post(f"/certificates/{first['id']}/revoke")

        assert response.status_code == 200
        detail = client.get(f"/identities/{identity['id']}").json()
        certificates = {item["id"]: item for item in detail["certificates"]}
        assert detail["identity"]["status"] == "active"
        assert detail["identity"]["certificate_fingerprint"] == second["fingerprint"]
        assert certificates[first["id"]]["status"] == "revoked"
        assert certificates[second["id"]]["status"] == "active"


def test_compromise_quarantines_revokes_and_recovers_with_replacement() -> None:
    with make_client() as client:
        identity = create_identity(client)
        original = issue_identity_certificate(client, identity)
        incident_response = client.post(
            "/incidents/compromise",
            json={"identity_id": identity["id"], "reason": "synthetic key compromise"},
        )

        assert incident_response.status_code == 201
        incident = incident_response.json()
        assert incident["status"] == "open"
        quarantined = client.get(f"/identities/{identity['id']}").json()
        assert quarantined["identity"]["status"] == "quarantined"
        assert quarantined["certificates"][0]["status"] == "revoked"

        recovery_response = client.post(f"/incidents/{incident['id']}/recover")
        assert recovery_response.status_code == 200
        recovered = recovery_response.json()
        assert recovered["incident"]["status"] == "resolved"
        assert recovered["identity"]["status"] == "active"
        assert recovered["certificate"]["status"] == "active"
        assert recovered["certificate"]["fingerprint"] != original["fingerprint"]

        event_types = [event["event_type"] for event in client.get("/audit/events").json()]
        assert "incident_opened" in event_types
        assert "certificate_replaced" in event_types
        assert event_types[-1] == "recovery_completed"


def test_only_active_identities_can_receive_certificates_or_open_incidents() -> None:
    with make_client() as client:
        identity = create_identity(client)
        quarantined = client.post(f"/identities/{identity['id']}/quarantine")
        assert quarantined.status_code == 200

        issue = client.post(f"/identities/{identity['id']}/certificates", json={})
        compromise = client.post(
            "/incidents/compromise",
            json={"identity_id": identity["id"], "reason": "duplicate compromise attempt"},
        )
        assert issue.status_code == 409
        assert compromise.status_code == 409


def test_audit_integrity_endpoint_verifies_and_detects_tampering() -> None:
    with make_client() as client:
        create_identity(client)
        verified = client.get("/audit/integrity")
        assert verified.status_code == 200
        assert verified.json() == {
            "valid": True,
            "event_count": 1,
            "checked_through_sequence": 1,
            "first_invalid_sequence": None,
            "error": None,
        }

        session = client.app.state.session_factory()
        try:
            event = session.scalar(select(AuditEventRecord))
            assert event is not None
            event.reason = "tampered after the fact"
            session.commit()
        finally:
            session.close()

        tampered = client.get("/audit/integrity")
        assert tampered.status_code == 200
        assert tampered.json()["valid"] is False
        assert tampered.json()["first_invalid_sequence"] == 1


def test_step_ca_health_fails_closed_when_cli_times_out() -> None:
    def timed_out_runner(command: list[str], **kwargs: object) -> CompletedProcess[str]:
        raise TimeoutExpired(command, timeout=10)

    client = StepCaClient(
        ca_url="https://step-ca:9000",
        root_path="/certs/root_ca.crt",
        password_file="/run/secrets/password",
        certificate_directory="/data/certificates",
        runner=timed_out_runner,
    )

    assert client.health() is False


def test_step_ca_issue_failure_handles_missing_cli_output(tmp_path) -> None:
    def failed_runner(command: list[str], **kwargs: object) -> CompletedProcess[str]:
        return CompletedProcess(command, 1, stdout=None, stderr=None)

    client = StepCaClient(
        ca_url="https://step-ca:9000",
        root_path="/certs/root_ca.crt",
        password_file="/run/secrets/password",
        certificate_directory=str(tmp_path),
        runner=failed_runner,
    )

    with pytest.raises(StepCaError, match="certificate issuance failed"):
        client.issue_certificate("agent-alpha", ["agent-alpha"])


def test_step_ca_revocation_uses_a_revoke_token() -> None:
    calls: list[list[str]] = []

    def runner(command: list[str], **kwargs: object) -> CompletedProcess[str]:
        calls.append(command)
        if "token" in command:
            return CompletedProcess(command, 0, stdout="generated\neyJhbGciOiJFUzI1NiJ9.eyJzdWIiOiIxIn0.signature\n", stderr="")
        return CompletedProcess(command, 0, stdout="revoked", stderr="")

    from app.integrations.step_ca import StepCaClient

    client = StepCaClient(
        ca_url="https://step-ca:9000",
        root_path="/certs/root_ca.crt",
        password_file="/run/secrets/password",
        certificate_directory="/data/certificates",
        runner=runner,
    )
    client.revoke_certificate("38C981A16B325B984707FA5F3948F3A3")

    assert calls[0][2:5] == ["token", "75483048652269599984228895836137386915", "--revoke"]
    assert "--provisioner-password-file" in calls[0]
    assert calls[1][2:6] == ["revoke", "75483048652269599984228895836137386915", "--token", "eyJhbGciOiJFUzI1NiJ9.eyJzdWIiOiIxIn0.signature"]
    assert "--provisioner-password-file" not in calls[1]
