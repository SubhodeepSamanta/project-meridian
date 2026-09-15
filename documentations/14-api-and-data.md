# API and data milestone

## Purpose

The API is Meridian's control-plane boundary. It records identities, requests certificates from the configured local `step-ca`, stores certificate metadata, changes lifecycle state, and exposes an ordered audit stream. The API never returns a private key or a private-key filesystem path.

## Implemented behavior

- `GET /health` checks both SQLite and the certificate authority.
- `POST /identities` registers a service or AI-agent identity with owner, purpose, and allowed actions.
- `GET /identities` and `GET /identities/{id}` return identities and safe certificate metadata.
- `POST /identities/{id}/certificates` requests a short-lived certificate from `step-ca` and records the result.
- `GET /certificates` lists safe certificate metadata.
- `POST /certificates/{id}/revoke` revokes through `step-ca`, then marks the certificate and identity revoked.
- `POST /identities/{id}/quarantine` isolates an identity and records the operator decision.
- `GET /audit/events` returns a deterministic sequence of events with a previous-hash link and current event hash.

## Why the layers exist

Routes translate HTTP into use-case inputs and outputs. Domain services contain decisions such as duplicate-name rejection and audit creation. The database layer keeps persistence details out of the routes. `StepCaClient` is an integration adapter: the rest of the application depends on an interface-like client, so tests can use a fake CA while the container uses the real `step` CLI.

The API container includes the `step` binary but does not mount the CA private-key directory. It can authenticate to the CA using the provisioner password file and the CA root trust file, while the CA process remains the only component with its encrypted signing keys. This is a useful local boundary, not a complete production secret-management design.

## Audit-chain intuition

Each event is numbered from one. Its hash is calculated from its identity, event fields, payload, and the hash of the previous event. If an old row is changed, the changed hash no longer matches the next event's `previous_event_hash`. This is tamper-evident ordering, not a replacement for an append-only external log or a full signature scheme.

## Verification commands

Build and run API tests inside the project image:

```powershell
docker compose build meridian-api
docker compose run --rm --no-deps meridian-api pytest -q
```

Run the real container path:

```powershell
docker compose up -d meridian-api
Invoke-RestMethod http://localhost:8000/health
```

The verification performed for this milestone registered a synthetic identity, issued a real certificate through the running `step-ca`, read the audit events, and confirmed that the response did not contain `key_path` or `private_key`. The observed status was healthy and the certificate was active.

## Problems found and fixed

1. SQLite cannot be trusted to generate a sequence for a non-primary integer column. The audit sequence is now explicitly assigned as `max(sequence) + 1` and constrained to be unique.
2. Returning SQLAlchemy objects through `__dict__` would expose ORM internals and could fail JSON serialization. Identity detail responses now map only approved metadata fields.
3. A stale `Request` type annotation remained after quarantine stopped needing the request object. Docker test collection caught the `NameError`; the unused parameter was removed and the image was rebuilt.
4. Adding the action result column exposed that `create_all` does not migrate an existing SQLite table. A backward-compatible startup migration now adds the missing column without deleting the already-created local evidence database.
5. The first tests used a fake CA so failure paths were deterministic. A second check used the real CA-backed API container so the adapter, mounted trust material, database, and HTTP boundary were verified together.

## Current limitations

- SQLite is appropriate for a local demonstration, not a concurrent production control plane.
- The local policy engine now evaluates named actions, but API authentication and an external authorization service are still out of scope for this POC.
- The API relies on a local password file for the synthetic CA provisioner.
- Audit events are hash-linked but are not yet exported to an independent immutable store.
- Certificate renewal scheduling, incident orchestration, and protected-key-store failure scenarios are still pending.
