# Incidents and recovery milestone

## Purpose

Meridian now demonstrates a complete compromise story for one synthetic identity: an incident opens, the identity is quarantined, active certificates are revoked, a replacement certificate is issued, and the identity is recovered with an audit trail.

## Lifecycle behavior

- Certificate responses expose `lifecycle_status` as `active`, `expiring_soon`, `expired`, `retired`, or `revoked`.
- `GET /certificates/expiring` finds active certificates inside the six-hour warning window or already expired.
- `POST /certificates/{id}/renew` issues a new certificate, retires the previous one, and updates the identity fingerprint.
- `POST /incidents/compromise` creates an open incident, quarantines the identity, revokes its active certificates through the CA, and records each step.
- `POST /incidents/{id}/recover` issues a replacement certificate, reactivates the identity, resolves the incident, and records `certificate_replaced` and `recovery_completed`.

The recovery endpoint requires the identity to remain quarantined. It cannot silently recover a different lifecycle state or reuse the revoked certificate.

## Verification

Run the deterministic live scenario with `pwsh -File .\scripts\run_incident.ps1`.

Expected output:

```text
COMPROMISE_CONTAINMENT: PASS
CERTIFICATE_REPLACEMENT: PASS
RECOVERY_EVIDENCE: PASS
Incident and recovery milestone passed.
```

Run the backend suite with `docker compose run --rm --no-deps meridian-api pytest -q`.

## Audit evidence

The scenario creates events for incident opening, quarantine, certificate revocation, replacement, and recovery. Each event is connected to the incident ID and the global hash-linked audit sequence. The dashboard can therefore tell a story from event evidence instead of using a hard-coded progress animation.

The revocation adapter uses a dedicated short-lived `step ca token --revoke` authorization token and then submits `step ca revoke --token ...`. This follows the current step CLI contract; the revoke command itself does not accept the provisioner-selection flags used for issuance.

During the first live run, revocation also exposed a serial-format bug: the API inventory stored hexadecimal serial text while the revoke CLI expects decimal serial input. New inventory values now use the CA's decimal serial representation, and the adapter converts legacy values containing hexadecimal letters for compatibility.

## Limitations

The CA uses passive/local revocation semantics for this POC; sample services do not yet query an OCSP responder. Recovery does not prove that an external target service has reloaded its certificate. Real deployments need coordinated rollout, revocation distribution, operator authentication, and independent incident storage.
