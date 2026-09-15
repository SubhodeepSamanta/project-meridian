# Study 03 — API, persistence, and evidence

This chapter explains the first application layer from basic concepts to the design tradeoffs that matter when the platform grows.

## 1. The basic mental model

Meridian has two kinds of work:

1. The certificate authority performs cryptographic work: it issues and revokes certificates.
2. The API performs governance work: it decides which record to change, stores the result, and gives a human-readable view of what happened.

The API is therefore a control plane, not the CA itself. A useful analogy is an airport control tower: it does not manufacture the aircraft, but it records who is allowed to move, coordinates the request, and keeps evidence of the decision.

## 2. Request flow

For certificate issuance, the path is:

```text
HTTP request
  -> FastAPI route validates shape
  -> identity status is checked
  -> StepCaClient calls the `step` CLI
  -> certificate metadata is parsed with cryptography
  -> database record and audit event are committed
  -> safe metadata is returned
```

The private key is created by `step-ca` tooling and stored in the API certificate directory, but the route response intentionally contains neither the key nor its path. A UI can show identity and certificate facts without becoming a key-distribution interface.

## 3. Why use an adapter

`apps/api/app/integrations/step_ca.py` isolates the external CLI. Production code uses the real adapter. Tests inject `FakeStepCaClient`, which lets us test duplicate identity, successful issuance, CA failure, and lifecycle changes without depending on the network or a running CA for every test. The real-container check then verifies that the adapter actually works with the mounted `step-ca` trust material.

This split is a general engineering pattern: make the boundary replaceable, but run at least one test through the real boundary.

## 4. Data model intuition

- An identity is the long-lived business record: name, owner, purpose, status, and allowed actions.
- A certificate is a time-bounded credential belonging to an identity.
- An audit event is an evidence record for a consequential action.
- An incident and action-request model are present as foundations for the next governance milestones.

The database stores certificate paths internally because the local simulator must later be able to renew or revoke them. Those paths are not part of the public response schema.

## 5. Hash-linked audit ordering

An audit record contains `sequence`, `previous_event_hash`, and `event_hash`. The first event has no predecessor. Each later event includes the predecessor hash in its own hashed material. The ordering is explicit rather than relying on timestamps, because two events can share a timestamp resolution and clocks can move.

This gives tamper evidence. It does not prove who wrote the database, prevent deletion, or provide an independent trusted timestamp. Those are intentional future exercises.

## 6. Commands used

Build the API image and run its tests:

```powershell
docker compose build meridian-api
docker compose run --rm --no-deps meridian-api pytest -q
```

For host-side development, use the repository-managed Windows virtual environment:

```powershell
pwsh -File .\scripts\setup_backend_venv.ps1
pwsh -File .\scripts\run_backend_tests.ps1
```

The Dockerfile creates the matching Linux environment at `/opt/venv`. Docker remains the integration environment, while `apps/api/.venv` gives the developer an isolated interpreter for fast edits and tests. Both install the pinned `apps/api/requirements.txt` contract.

Start the real services and inspect health:

```powershell
docker compose up -d meridian-api
Invoke-RestMethod http://localhost:8000/health
```

The manual verification also called `POST /identities`, `POST /identities/{id}/certificates`, and `GET /audit/events` with synthetic data. It returned healthy dependencies, an active certificate, and an audit sequence containing registration followed by issuance.

## 7. Problems and lessons

- A stale type annotation caused test collection to fail before a single test ran. Static importability is a separate quality gate from behavioral tests.
- A first implementation attempted to rely on implicit SQLite integer behavior for audit ordering. Explicit sequence assignment is clearer for a local SQLite POC and makes the evidence contract visible.
- Serializing an ORM object's `__dict__` would have leaked `_sa_instance_state` and coupled the API to SQLAlchemy internals. Explicit response mapping is slightly more code but safer and more stable.
- Fake-CA tests alone could have missed a broken executable path, trust mount, or provisioner configuration. The real API container check caught those classes of integration problem.
- Adding `result_payload` to the action table exposed an important migration lesson: SQLAlchemy `create_all` creates missing tables but does not alter an existing table. A small startup migration adds this nullable-in-practice defaulted field while preserving existing synthetic evidence.

## 8. What is not solved yet

The local API is not authenticated and the action executor is a deterministic simulator rather than a real target-service call. The local password-file arrangement is not an HSM. Those are constraints, not hidden claims of production readiness. The policy endpoint now adds the key concept that a matching certificate fingerprint proves *which* registered identity requested an action, while policy decides *what* it may do.
