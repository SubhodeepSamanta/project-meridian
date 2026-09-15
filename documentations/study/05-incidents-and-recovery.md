# Study 05 — expiry, compromise, replacement, and recovery

## Why lifecycle matters

A certificate is not a permanent identity. It has a validity interval, and an identity can become unsafe before that interval ends. A resilient trust system needs both time-based maintenance and incident-driven containment.

Meridian exposes two related paths:

- Renewal is routine maintenance: the identity remains active, the old certificate is retired, and a fresh certificate is issued.
- Recovery is incident response: the identity is quarantined, its active certificate is revoked, and only then is a fresh replacement issued as part of an explicit recovery operation.

## Healthy-to-recovered story

```text
active identity + active certificate
    -> compromise detected
open incident + quarantined identity
    -> CA revocation
revoked original certificate
    -> operator recovery
new active replacement certificate + resolved incident
```

The distinction between `retired` and `revoked` is intentional. Retirement is a normal replacement; revocation indicates that the old credential should no longer be trusted.

## Expiry intuition

The API derives lifecycle status from `not_after` and the current UTC time. It does not mutate the stored status merely because time passed. This keeps evidence of the stored lifecycle state separate from a live observation. The expiring endpoint filters active certificates whose observed state is `expiring_soon` or `expired`.

## Compromise flow

1. Create an incident with a reason and identity.
2. Mark the identity quarantined before further use.
3. Ask the CA to revoke each active certificate.
4. Record success or failure for every revocation.
5. Keep the incident open until a replacement certificate is tested.
6. Issue the replacement through the same CA adapter.
7. Reactivate the identity, resolve the incident, and record recovery.

The ordering creates a safety pause. If replacement issuance fails, the identity stays quarantined and the incident stays open.

## Commands used

Run the complete scenario with `pwsh -File .\scripts\run_incident.ps1`.

The script uses `Invoke-RestMethod` to call the real API container. It deliberately generates a unique identity name on each run, checks the original certificate becomes revoked, checks the replacement fingerprint differs, and verifies the incident inventory says `resolved`.

Run the automated backend tests with `docker compose build meridian-api` followed by `docker compose run --rm --no-deps meridian-api pytest -q`.

## Problems and design lessons

Renewal and recovery initially exposed a testing issue: the fake CA returned the same serial and fingerprint for every issuance, which violated the database's unique fingerprint constraint. The test double was corrected to produce deterministic but distinct metadata per issuance. This preserves repeatability while exercising the same uniqueness rule as the real CA.

The recovery path deliberately issues while the identity is quarantined, but only through the dedicated recovery endpoint. The ordinary issuance endpoint rejects quarantined identities. That separation prevents a generic certificate request from bypassing the incident workflow.

The first live containment attempt also found that revocation is not the same CLI shape as issuance. The revoke command does not take `--provisioner` and `--provisioner-password-file` in this version. The adapter now creates a short-lived revoke token with `step ca token --revoke` and submits it with `step ca revoke --token`. The same check found that the API had stored hexadecimal serials while the CLI expected decimal serials; new values use decimal and legacy hex values are converted when they contain hexadecimal letters.

## Limits

This local demo does not implement a distributed revocation protocol, reload certificates inside every workload, or prove human operator identity. It shows the state machine and evidence needed to build those features safely.
