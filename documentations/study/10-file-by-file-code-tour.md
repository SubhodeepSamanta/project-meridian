# Study 10 — file-by-file and function-by-function code tour

This is the source-reading chapter. It is intentionally more granular than the milestone chapters. It follows the code in the order a request travels through the system and explains every meaningful executable block: imports, constants, classes, fields, functions, route decorators, state transitions, error paths, and verification assertions.

The line ranges below refer to the current repository snapshot. Function names are the more durable reference because line numbers move when a comment or import is added. Blank lines, generated lock-file entries, and compiler output are not repeated; every source-level behavior is covered.

## 1. First build the mental model

The whole system is a chain of boundaries:

```text
browser
  -> Vite development server and /api proxy
  -> FastAPI route
  -> request validation and database session
  -> domain decision or step-ca integration
  -> SQLite state plus hash-linked audit event
  -> JSON response
  -> React state refresh and visual evidence
```

There are two certificate authorities in the lab. `step-ca` is the ordinary local CA used by the API and mTLS simulators. `hsm-ca` is a separate protected-key demonstration using `step-ca:hsm` plus SoftHSM2. Keeping them separate prevents the learning experiment from silently becoming the trust root for the rest of the demo.

When reading any function, ask four questions:

1. What enters this function, and which type or validation guarantees already exist?
2. What state does it read or change?
3. What security decision does it make?
4. What evidence is written if it succeeds or fails?

## 2. Infrastructure files: how the lab exists

### `docker-compose.yml`

This is the runtime topology, not application business logic.

- Lines 1–23 define `step-ca`. The pinned image makes the demo repeatable. Port `9000` is exposed for host inspection. The bind mount puts generated CA state under the ignored runtime directory. The healthcheck runs `step ca health` against the CA root, so “container running” is not confused with “CA ready.”
- Lines 25–50 define `service-a`. It uses the stock Python image and mounts the simulator read-only. Environment variables tell the simulator its name, port, peer, certificate, private-key, and trusted-root paths. `depends_on` waits for a healthy CA, while its healthcheck proves an mTLS client can call its own endpoint.
- Lines 52–77 repeat the same contract for `service-b`, with the peer direction reversed. The duplication is deliberate: two independent identities make mutual TLS visible, and both services now report readiness.
- Lines 79–104 define `meridian-api`. The Docker build comes from `apps/api`. The database is mounted at `/data`, while the CA root and provisioner password are read-only mounts. The API receives service-to-service DNS name `step-ca`, not host `localhost`; its healthcheck requires a healthy JSON response from the API itself.
- The API also receives the HSM CA URL and public HSM root certificate. Only `/certs/hsm` is mounted; HSM secrets and token files are not mounted into the API container.
- Lines 106–120 define `hsm-ca`. The custom image installs SoftHSM2 into the CGO-enabled `step-ca:hsm` image. The token directory is mounted separately from the CA configuration so the script can remove only the token boundary during the failure test.
- Lines 122–141 define `meridian-web`. The source is mounted for a fast local loop, while a named volume keeps `node_modules` inside Docker. `npm ci` follows the lockfile on each container start, `VITE_API_TARGET=http://meridian-api:8000` points at the Compose service, and the healthcheck verifies the Vite server. `localhost` inside this container means the web container itself.
- Lines 143–144 declare the named dependency volume. It is cache, not source, and is intentionally absent from Git.

The important Compose lesson is namespace awareness. A URL that works from Windows may fail inside a container, and a path that exists on Windows must be translated into the container mount path before application code can use it.

### `apps/api/Dockerfile`

- Line 1 starts a `step_cli` build stage from the same pinned CA image.
- Line 3 starts the smaller Python runtime stage.
- Line 5 copies only the `step` executable into the Python image. The API can call the CLI without installing an entire CA image as its application runtime.
- Lines 7–9 choose `/app` and copy the dependency manifest.
- Lines 10–12 create `/opt/venv` inside the image and install Python dependencies there without retaining pip's cache. The `PATH` environment variable makes every later `pytest`/`uvicorn` command use that environment.
- Lines 13–14 copy application and test source. Including tests in the image allows the exact runtime image to run `pytest`.
- Line 16 gives Uvicorn's default command; Compose can override it explicitly.

### `infrastructure/softhsm/Dockerfile`

- Line 1 selects the CGO-enabled HSM variant required by Smallstep's PKCS#11 path.
- Line 3 switches to root only for package installation.
- Lines 5–9 install `softhsm2` and `opensc`, remove apt metadata, create the token directory, and write a file-backed SoftHSM configuration.
- Line 11 exposes the configuration path to SoftHSM tools.

SoftHSM is a software model of an HSM boundary. It is useful for API and integration learning, but it does not provide the tamper resistance, operational controls, or certification of a physical HSM.

## 3. API bootstrap and configuration

### Empty `__init__.py` files

`apps/api/app/__init__.py`, `app/api/__init__.py`, `app/api/routes/__init__.py`, `app/core/__init__.py`, `app/domain/__init__.py`, each domain subpackage initializer, `app/db/__init__.py`, and `app/integrations/__init__.py` are intentionally empty. Their job is package structure: Python can import modules using stable names such as `app.db.models`. They do not hide initialization side effects.

### `apps/api/app/core/config.py`

- Lines 1–2 import the dataclass decorator and `os` environment access.
- Lines 5–15 define frozen `Settings`. Frozen means a running app cannot accidentally mutate its configuration object.
- Each field reads an environment variable and has a local default: database URL, CA URL, trusted root path, password-file path, certificate output directory, and optional HSM CA URL/root paths. Empty HSM settings keep isolated unit tests from probing a real container.
- `Settings` contains locations and connection values, not secret contents. The password is mounted as a file and never placed in source.
- Line 18 creates one default `settings` object for production-like startup. Tests can pass a different `Settings` object to `create_app`.

### `apps/api/app/db/database.py`

This file is separate from the models so connection policy and table definitions do not become one tangled module.

- Lines 1–6 import the generator type, SQLAlchemy engine helpers, ORM base/session types, and `StaticPool`.
- Lines 9–10 define `Base`, the declarative parent from which every model inherits. `pass` is correct: the class exists to carry SQLAlchemy metadata.
- `create_database` at lines 13–27 accepts a URL and returns both an `Engine` and a `sessionmaker`.
  - Lines 14–15 start with empty optional dictionaries.
  - Lines 16–20 add SQLite's cross-thread setting and use `StaticPool` for in-memory tests. Without `StaticPool`, a test-created schema can disappear across connections.
  - Lines 21–25 construct the engine with those options.
  - Line 26 creates sessions that do not autoflush unexpectedly and do not expire returned objects after commit.
  - Line 27 returns both pieces so startup and request dependencies share the same database contract.
- `ensure_schema` at lines 30–46 creates missing tables and applies the one small backward-compatible POC migration.
  - Line 32 calls `Base.metadata.create_all`; this creates missing tables but does not alter existing tables.
  - Lines 33–34 avoid SQLite-specific migration SQL for other databases.
  - Lines 36–38 inspect `action_requests` and look for `result_payload`.
  - Lines 39–45 add that column with a safe JSON-object default when an older local database is reused.
- `session_scope` at lines 48–53 creates one session, yields it to a caller, and closes it in `finally`. The `finally` matters when a route raises.

### `apps/api/app/db/models.py`

The ORM models are the durable nouns of the system.

- Lines 1–7 import time types, generic payload typing, SQL types, ORM mapping helpers, and `Base`.
- `utc_now` at lines 10–11 gives all timestamp defaults an explicit UTC timezone.
- `IdentityRecord` at lines 14–32 maps the owner-controlled identity registry. `name` is unique; `kind` distinguishes `service` from `agent`; `purpose` explains intent; `status` is the lifecycle gate; `allowed_actions` is JSON text for this small SQLite POC; `certificate_fingerprint` binds the current credential; timestamps support history. The relationship at lines 30–32 lets SQLAlchemy load a parent's certificates and deletes children with the identity.
- `CertificateRecord` at lines 35–53 stores certificate metadata and lifecycle state. The private key path is inventory metadata only; API responses never return the key. `identity_id` is the foreign key to the identity. Serial, fingerprint, validity, algorithm, and issuer make certificate reasoning inspectable.
- `ActionRequestRecord` at lines 56–69 records intent before or after policy. `risk_level`, `approval_status`, and `decision` are separate because “high risk,” “awaiting approval,” and “allowed” are different facts. `result_payload` holds the deterministic simulated outcome.
- `IncidentRecord` at lines 71–79 records a compromise story, its target identity, open/resolved state, reason, and resolution timestamp.
- `AuditEventRecord` at lines 82–99 is the evidence spine. It stores actor, subject, result, correlation, optional incident, JSON payload, previous hash, current hash, unique sequence, and timestamp. `sequence` is explicit and unique so ordering is not inferred from an arbitrary database row order.
- `safe_payload` at lines 102–103 turns `None` into `{}`. This keeps JSON serialization stable and avoids storing a null where the API promises an object.

### `apps/api/app/schemas.py`

Pydantic schemas are the boundary between untrusted JSON and typed application data.

- Lines 1–4 import datetime, `Literal`, and Pydantic primitives.
- `IdentityCreate` lines 7–12 restrict kind to two known values and bound name, owner, purpose, and action-list shapes.
- `CertificateIssueRequest` lines 15–17 makes SANs optional, gives a short default lifetime, and restricts validity to step-ca duration syntax such as `24h`.
- `ActionRequestCreate` lines 20–27 requires action, target, and a 64-character hexadecimal SHA-256 certificate fingerprint. The fingerprint is not decorative: the route compares it with the identity's current binding.
- `ActionRequestResponse` lines 26–38 enables ORM attribute reading and exposes the safe action result.
- `IncidentCreate` lines 41–43 requires an identity and a bounded reason.
- `IncidentResponse` lines 46–54 represents open or resolved incident state.
- `IdentityResponse` lines 57–68 exposes safe identity metadata and the parsed allow-list.
- `CertificateResponse` lines 71–86 exposes lifecycle status and cryptographic metadata without private-key material.
- `AuditEventResponse` lines 89–104 exposes parsed payload plus both hash-link fields and sequence. `AuditIntegrityResponse` reports whether the complete chain was recomputed successfully and where validation stopped if not.

## 4. Database session, domain logic, and the CA boundary

### `apps/api/app/api/dependencies.py`

`get_session` at lines 7–12 is FastAPI's request-scoped dependency. It retrieves the session factory from `app.state`, yields one session to the route, and closes it even on exceptions. Routes ask for `Session = Depends(get_session)` instead of constructing sessions themselves.

### `apps/api/app/domain/audit/service.py`

`AuditService.record` and `AuditService.verify` are the audit invariants in one place.

- Lines 14–26 define required evidence fields and optional correlation/incident/payload metadata.
- Lines 27–29 fetch the previous highest-sequence event so the next event can point backward.
- Line 30 obtains the maximum sequence; empty tables use zero.
- Line 31 creates the event UUID.
- Line 32 normalizes the payload.
- Lines 33–44 construct the exact canonical material to hash. `sort_keys=True` later means dictionary insertion order cannot change the digest.
- Lines 45–47 serialize compactly and compute SHA-256.
- Lines 48–61 construct the ORM record, repeating the fields that must be queryable and storing the hash-link values.
- Lines 62–64 add and flush the record. Flush makes the event visible inside the current transaction without committing the caller's larger state change.
- `verify` reads events in sequence order, checks contiguous numbering and predecessor links, parses payload objects, rebuilds the canonical material, and compares every stored SHA-256 hash. It returns a structured first-failure result instead of raising a generic error.
- The final line creates the shared `audit_service` instance.

This is tamper-evidence, not an external immutable log. A database administrator could rewrite both rows and hashes. The advanced chapter explains what production would add.

### `apps/api/app/domain/identities/service.py`

- `IdentityConflictError` lines 11–12 gives the route a domain-specific conflict to translate into HTTP 409.
- `register_identity` lines 15–49 first checks the unique name at lines 26–27.
- Lines 29–36 build a UUID-backed record and sort/deduplicate the action list before JSON encoding.
- Lines 37–46 add the identity and immediately record `identity_registered` evidence.
- Lines 47–49 commit, refresh, and return the database-backed object.

The distinction is important: the domain service owns registration rules and audit side effects; the route owns HTTP translation.

### `apps/api/app/domain/policy/service.py`

- Lines 9–15 define deterministic high- and medium-risk action sets. Unknown actions are low risk, but they still need an identity allow-list entry.
- `PolicyDecision` lines 18–24 groups the four outputs of policy so callers cannot accidentally forget the approval state.
- `risk_for_action` lines 26–31 maps one action to one risk label.
- `evaluate_action` lines 34–66 is a short-circuit policy pipeline: lines 35–41 calculate risk and deny inactive identities; lines 44–51 parse the allow-list and deny missing permission; lines 53–59 turn an allowed high-risk request into `approval_required`; lines 61–66 allow remaining permitted actions.
- `execute_simulated_action` lines 69–76 returns a deterministic proof object. It does not call a real target, which keeps the demo safe and repeatable.

### `apps/api/app/integrations/step_ca.py`

This adapter keeps CLI details out of routes.

- Lines 1–13 import regex, subprocess, dataclasses, time, path, sequence typing, UUIDs, and X.509 parsing.
- `StepCaError` lines 15–16 is the integration failure type.
- `IssuedCertificate` lines 19–29 is a safe value object containing paths and public metadata.
- `_safe_name` lines 32–34 converts arbitrary identity names to filesystem-safe prefixes and supplies `identity` if a name collapses to empty.
- `_as_utc` lines 37–40 normalizes naive or offset-aware timestamps.
- `_serial_for_revoke` lines 43–47 preserves decimal serials and converts legacy hexadecimal inventory values to the decimal CLI form.
- `StepCaClient.__init__` lines 51–63 stores endpoints, paths, the certificate directory, and an injectable runner. Injection makes subprocess behavior testable without a live CA.
- `_run` centralizes bounded subprocess execution and converts missing executables, timeouts, and other subprocess failures into `StepCaError`.
- `health` runs `step ca health` with root verification, captures output, uses a timeout, and fails closed to `False` when the CLI is unavailable instead of turning dependency loss into an API 500.
- `issue_certificate` lines 83–139 creates unique output paths, constructs and runs `step ca certificate`, appends every SAN, bounds the timeout, parses the PEM, and extracts serial, subject, issuer, validity, public-key algorithm, and SHA-256 fingerprint. The private key remains only at the ignored runtime path.
- `revoke_certificate` lines 141–193 implements the two-step CLI contract: normalize serial; request a short-lived revoke token; reject a missing token; pass serial plus token to `step ca revoke`; translate all nonzero results into `StepCaError`.

## 5. API startup and each route file

### `apps/api/app/main.py`

`create_app` lines 9–31 is dependency composition. Lines 13–14 create the engine/session factory and schema. Lines 16–24 create FastAPI and put engine, session factory, and either an injected fake or real `StepCaClient` into application state. Lines 25–30 register route modules. Line 34 creates the Uvicorn module-level app.

The injected client is the seam between fast unit tests and real Docker integration tests.

### `apps/api/app/api/routes/health.py`

`health` lines 10–27 performs two independent checks. Lines 12–19 execute `select 1` and close the session; lines 21–22 call the CA adapter and combine both statuses; lines 23–27 return structured JSON. “Degraded” is more useful than a false all-good response when either dependency is unavailable.

### `apps/api/app/api/routes/protected_boundary.py`

`protected_boundary` exposes a small operator-facing description of the protected signing boundary. It calls the configured HSM CA's certificate-verified health command, then returns the synthetic token label, PKCS#11 object names, and the API's intentionally unmounted disk-key boundary. It reports `unavailable` when the HSM CA is not configured or cannot be reached; it does not expose a PIN, private key, or token file.

### `apps/api/app/api/routes/identities.py`

- `to_identity_response` lines 17–28 maps ORM fields and parses JSON action text.
- `create_identity` lines 31–48 accepts validated JSON, calls domain registration, converts a duplicate to HTTP 409, and returns the safe DTO.
- `list_identities` lines 51–54 queries creation order and maps every row.
- `get_identity` lines 57–84 loads one identity, rejects missing IDs, loads its certificates, and returns a manually selected certificate field set.
- `quarantine_identity` lines 87–108 rejects missing/revoked identities, changes state, records evidence, commits, and returns the safe identity.

### `apps/api/app/api/routes/certificates.py`

- `to_certificate_response` lines 18–33 maps metadata and calls the derived lifecycle helper.
- `certificate_lifecycle_status` lines 36–47 preserves explicit `revoked`/`retired`, normalizes timezones, distinguishes expired from expiring within six hours, and otherwise returns active.
- `list_certificates` lines 50–55 returns certificates in creation order.
- `list_expiring_certificates` lines 58–71 queries active records and applies the expiry predicate.
- `issue_certificate` loads the identity, requires the exact `active` state, chooses SANs, calls step-ca, retires any previous active credentials, audits integration failure/success, updates the current fingerprint, commits, refreshes, and returns.
- `revoke_certificate` is idempotent for already-revoked rows, delegates the CA operation, audits failures, marks the certificate revoked, and revokes the identity only when that certificate is its current fingerprint.
- `renew_certificate` blocks retired/revoked certificates and inactive identities, issues a replacement, retires all prior active records, binds the new fingerprint, audits both IDs, commits, and returns old/new evidence together.

### `apps/api/app/api/routes/actions.py`

- `to_action_response` lines 18–30 maps the database row and parses stored result JSON.
- `_new_action_request` lines 33–51 centralizes UUID and field construction so all decision branches produce the same record shape.
- `list_actions` lines 54–59 returns ordered action history.
- `request_action` lines 67–149 loads the identity, compares the presented fingerprint before policy, calls `evaluate_action`, creates the request, executes/audits allowed actions, audits approval-required requests, audits denials, commits, refreshes, and serializes.
- `approve_action` lines 152–198 requires a pending action, rechecks that the identity is active, changes approval/decision, executes the simulation, audits operator approval, commits, and returns.
- `deny_action` lines 201–227 requires a pending action, changes it to denied, records operator evidence, commits, and returns.

The fingerprint comparison proves credential-to-identity binding. The policy service separately proves identity-to-authority binding.

### `apps/api/app/api/routes/incidents.py`

- `to_incident_response` lines 20–28 exposes only incident fields.
- `list_incidents` lines 31–36 returns chronological incident records.
- `open_compromise_incident` lines 39–115 validates the target, creates the incident, quarantines immediately, records incident/quarantine evidence, selects active certificates, revokes each through the CA, records failures without hiding them, marks successful rows revoked, commits, and returns the incident.
- `recover_incident` lines 118–198 validates an open incident and quarantined identity, issues a replacement, preserves a failure audit if issuance fails, creates replacement metadata, reactivates the identity, resolves the incident with UTC time, records replacement/recovery events, commits, and returns all three updated objects.

### `apps/api/app/api/routes/audit.py`

`list_events` queries sequence order and explicitly rebuilds each response. `json.loads` turns stored payload text back into an object. `audit_integrity` delegates to `AuditService.verify` and exposes the result as a read-only evidence check. Returning both hash fields lets the dashboard show a genesis event versus a linked event while the integrity response says whether those links are valid.

## 6. The mTLS simulator

### `simulators/services/service.py`

- Lines 1–18 import HTTP, JSON, environment, sockets, SSL, and threading primitives.
- `client_common_name` lines 21–27 asks the TLS socket for the peer certificate and extracts its common name. Missing certificate data becomes `None` rather than a crash.
- `call_peer` lines 30–45 creates an SSL context that requires a server certificate, loads the trusted root and client certificate/key, connects to the peer, sends an HTTP request, and returns a small JSON result. This proves both server and client authentication.
- `ServiceHandler` lines 48–89 handles HTTP. `send_json` lines 49–55 writes JSON with content type/length; `do_GET` lines 57–89 serves health, peer calls, and 404s while converting peer failures into 502; `log_message` lines 91–93 uses a compact prefix.
- `create_server` lines 95–108 reads environment configuration, creates an SSL server context, requires client certificates, loads the keypair and trusted root, wraps the listening socket, and returns a threaded server.

The key teaching line is the server context's client-certificate requirement. Server-only TLS encrypts; mTLS authenticates both directions.

## 7. PowerShell orchestration scripts

Every script changes into the repository root first and uses an `Invoke-RequiredCommand` helper that runs a command, checks `$LASTEXITCODE`, and throws instead of printing a misleading success.

### `scripts/run_all_checks.ps1`

- Lines 1–4 enable stop-on-error, resolve the root, and define the helper.
- Lines 19–27 run Compose validation, local backend-venv tests, foundation, mTLS, API image/tests, policy, HSM, and incident checks in that order.
- Lines 28–47 build the frontend, start API/web, poll `/api/health` for up to 30 seconds while Vite becomes ready, and fail with web logs if the proxy never becomes healthy.
- Line 41 prints `FULL_STACK_CHECKS: PASS` only after every earlier command succeeded.

### `scripts/run_foundation.ps1`

- Lines 1–11 resolve ignored runtime directories and the artifact path.
- `Invoke-RequiredCommand` lines 13–25 is the common checked-command wrapper.
- Lines 27–35 generate a random bootstrap secret using the OS RNG and write it only to an ignored temporary/runtime path.
- Lines 38–87 initialize the CA with one consistent password, move the password into the ignored runtime secret path, start Compose, and wait for a healthy CA.
- Lines 89–157 issue a short-lived test certificate, inspect it through an isolated OpenSSL container, and verify the chain.
- Lines 176–178 print only safe artifact metadata and explicitly say the private key is excluded from Git.

### `scripts/run_mtls.ps1`

- Lines 1–27 resolve artifacts, ensure the CA is running, and define command checking.
- `Issue-ServiceCertificate` lines 29–65 calls the CA for each service, creates SANs, and keeps key/certificate outputs in ignored runtime storage.
- Lines 67–92 start both services and wait for them.
- Lines 94–124 make an authenticated client request to `/call-peer`.
- Lines 126–142 send a real HTTP request without a client certificate and read from the socket; this is why the negative test catches handshake failure where it actually surfaces.
- Lines 144–146 print the expected result markers.

### `scripts/run_policy.ps1`

- Lines 1–30 start the API and define JSON request helpers.
- `New-DemoIdentity` lines 32–47 posts an agent with an allow-list.
- `New-DemoCertificate` lines 49–64 asks for a short-lived certificate and returns safe metadata.
- Lines 66–96 submit an allowed action, an unallowed action, and a high-risk allowed action; the third remains pending until explicit approval.
- Lines 99–102 print the three policy acceptance markers.

### `scripts/run_incident.ps1`

- Lines 1–16 start the API and define the HTTP helper.
- Lines 18–38 create a unique agent and original certificate.
- Lines 40–52 open compromise and verify quarantine/revocation.
- Lines 54–67 recover the incident, verify active status and a distinct replacement fingerprint, and verify resolved evidence.
- Lines 69–72 print containment, replacement, and recovery markers.

### `scripts/run_hsm.ps1`

- Lines 1–12 resolve the HSM runtime, ignored secret paths, token directory, and artifacts.
- `Invoke-RequiredCommand` lines 14–25 makes each Docker call fail loudly.
- `New-RandomSecret` lines 27–31 creates random CA/PIN material.
- `Ensure-SecretFile` lines 33–42 creates a secret only when one does not already exist, which makes repeat runs stable.
- Lines 44–70 build the HSM image, inspect SoftHSM slots, and initialize exactly the expected token label.
- Lines 72–115 initialize the HSM CA when needed, create root/intermediate PKCS#11 objects, generate certificates through those objects, and update `ca.json` to use the intermediate object.
- Lines 117–127 remove temporary disk key files once config points at PKCS#11.
- Lines 129–155 start the CA and wait for health.
- Lines 157–170 issue an HSM-backed certificate and inspect PKCS#11 objects.
- Lines 172–176 assert no root/intermediate CA key file is on disk.
- Lines 178–201 stop the CA, move the token directory away, start it, and require a non-running state. `finally` restores the token even on failure.
- Lines 202–216 restart the restored CA, resolve the current service container with `docker compose ps -a -q`, and wait for healthy state. The `-a` matters because a failed token-loss attempt may leave the service stopped while the probe is selecting its container.
- Lines 217–220 print signing, no-disk-key, and expected-failure markers.

## 8. React, Tailwind, and the 3D dashboard

### `apps/web/index.html`

This file is not the dashboard UI. Vite needs one small HTML document with a `<div id="root">`; React takes over that element from `src/main.tsx`. The visual interface is React. Tailwind is compiled from the React source and CSS files. Keeping this shell small is the normal React architecture, not a return to hand-built HTML pages.

### `apps/web/package.json`

The scripts run Vite development, TypeScript build, and preview. React/ReactDOM provide the component runtime; Vite and its React plugin provide the pipeline; TypeScript and type packages provide compile-time checks; Tailwind CSS, PostCSS, and Autoprefixer provide utility generation. `package-lock.json` records the exact dependency graph; `node_modules` is not source.

### `apps/web/tailwind.config.js`

The content globs tell Tailwind where class names exist. The theme extends Manrope/DM Mono fonts, Meridian colors, and named aura/panel shadows. Custom names such as `meridian-cyan` keep JSX readable while preserving the visual system. No plugin is needed for this POC.

### `apps/web/postcss.config.js`

The two plugins process `@tailwind` directives and add browser prefixes. Vite reads this automatically during the build.

### `apps/web/vite.config.ts`

- Lines 1–2 import Vite's config helper and React plugin.
- Lines 4–5 enable JSX transformation.
- Lines 6–15 configure port 5173 and the `/api` proxy.
- Line 10 chooses the container target when Compose provides it and localhost for host development.
- Line 12 strips `/api` before forwarding, so browser code can consistently call `/api/health` while FastAPI receives `/health`.

### `apps/web/src/main.tsx`

Lines 1–4 import React, ReactDOM, the root component, and CSS. Lines 6–9 find `#root`, create a concurrent React root, and render `<App />` in strict mode. This is the bridge from the HTML mount shell to the React application.

### `apps/web/src/api.ts`

- Lines 1–80 define TypeScript mirrors of health, identity, certificate, action, incident, audit, and aggregate snapshot JSON.
- `request<T>` lines 84–100 is the typed fetch boundary. It merges JSON headers, preserves caller options, converts non-2xx responses into useful errors, and returns decoded JSON as `T`.
- `loadSnapshot` requests eight resources concurrently with `Promise.all`, including audit integrity and the protected-boundary status; the dashboard gets one coherent refresh cycle.
- `createIdentity` lines 114–122 posts a validated identity payload.
- `issueCertificate` lines 124–129 posts one SAN and the 24-hour demo lifetime.
- `quarantineIdentity` lines 131–133 posts the lifecycle transition.
- `requestAction` lines 135–143 sends intent plus the current certificate fingerprint.
- `approveAction` lines 145–147 posts operator approval.
- `openCompromise` lines 149–154 opens a synthetic incident.
- `recoverIncident` lines 156–161 posts recovery and types the three returned objects.

### `apps/web/src/App.tsx`

- Lines 1–16 import React hooks, API types, and operations.
- Lines 18–25 define a safe empty initial snapshot so the first render has no fake security data.
- `formatAge` and `formatDate` guard against invalid timestamps; `shortId` abbreviates long identifiers; `tone` maps domain states plus audit verification to semantic colors.
- `StatusPill` lines 53–55 and `SectionEyebrow` lines 57–59 are the two reusable presentational components.
- `App` owns the live screen.
  - Its state covers the API snapshot, selected identity, operator notice, connection error, current busy operation, demo phase, and evidence-view toggle.
  - `DemoPhase` and `demoPhaseCopy` name the four visible phases of the showcase: registering, issuing, evaluating, and approval. They are presentation state only; the API remains authoritative.
  - `refresh` loads the eight-resource API snapshot, clears connection errors, preserves a still-existing selection, defaults to the latest demo Alpha when present (otherwise the newest identity), and serializes overlapping polls so a slow request cannot overwrite the screen with stale data.
  - The `useEffect` at lines 80–84 performs an immediate load, starts a five-second poll, and cleans up the interval.
  - Derived values select the active certificate, foreground the newest twelve identities, calculate pending approvals/open incidents/expiry radar, detect certificate and containment evidence, calculate narrative progress, and build the live execution checkpoints.
  - `perform` lines 100–112 centralizes busy-state handling, notices, refresh-after-write, error display, and cleanup.
  - `launchStory` creates unique Alpha and Beta agents, updates the visible phase before each network group, issues both certificates, performs Alpha's allowed read, records Beta's denied delete attempt, submits Alpha's high-risk rotation request, selects Alpha, refreshes, and tells the operator that the approval gate is waiting.
  - `identityAction` lines 147–153 finds an active credential for a registry row.
  - Lines 155–180 render the fixed rail, brand, navigation, topbar, poll indicator, and health status.
  - Lines 182–209 render the hero and CSS 3D constellation. Orbit rings, connecting lines, four live nodes, a central Meridian node, and a legend create depth without a heavy rendering library.
  - Lines 211–216 render active identities, expiry radar, incident count, and audit sequence.
  - Lines 218–223 render Observe → Decide → Contain → Recover progress; `storyStep` never pretends recovery happened.
  - The identity registry renders the newest twelve records for a readable opening view while showing the full total. Rows are real buttons, selected state is explicit, and permissions become tags.
  - The selected identity panel renders a certificate dossier with issuer, algorithm, serial, expiry, and SHA-256 fingerprint. These are safe certificate metadata; private key material is never returned.
  - The boundary section renders live `hsm-ca` status, token/object metadata, the “not mounted” API disk-key fact, and the visible `API request -> HSM sign -> certificate returned` path; it is explanatory UI over an API health check, not a mock signing operation.
  - Incident theatre names “isolate the unknown” and renders the containment/recovery track from the actual incident status before offering the real recovery endpoint.
  - The audit surface renders the optional full sequence, hash-link indicator, verified-chain badge, and honest synthetic/local footer.
- The final line exports the root component.

### `apps/web/src/styles.css`

- The first lines import the two display fonts and Tailwind's base/components/utilities layers.
- The `:root` block defines ink, muted/faint text, deep backgrounds, translucent panels, border strengths, semantic colors, and the monospace face.
- Global rules establish box sizing, scrolling, safe button/link inheritance, disabled behavior, and the radial/grid background.
- Rail, content, hero, metric, story, registry, detail, incident, decision, and evidence selectors provide the editorial composition.
- `.constellation-card`, `.constellation-stage`, `.orbit-*`, `.constellation-line`, `.constellation-node`, and `.constellation-center` create the 3D scene. `perspective`, `transform-style: preserve-3d`, `translateZ`, and keyframe rotations create depth.
- Tailwind utility classes in `App.tsx` own rounded panels, shadows, semantic focus rings, responsive utility scanning, and custom palette names. The bespoke rules remain for geometry, glow, grid background, and tuned motion.
- Media queries collapse the grid, convert the fixed rail into a readable top navigation below 720px, enlarge small labels, hide lower-priority columns, stack touch actions below 460px, and convert the story track to a vertical timeline on small screens. The reduced-motion query disables animation when requested.

## 9. Tests: why each helper and test exists

### `apps/api/tests/test_api.py`

- `FakeStepCaClient` lines 11–44 provides deterministic health, issuance, and revocation without shelling out. `issue_count` makes each fake certificate different so renewal and recovery cannot accidentally reuse an old identity.
- `test_protected_boundary_is_explicit_when_not_configured` verifies that an isolated app reports the HSM boundary honestly instead of claiming it is healthy.
- `test_step_ca_issue_failure_handles_missing_cli_output` verifies a failed CA subprocess with empty stdout/stderr becomes a controlled `StepCaError`, not a secondary string-slicing exception.
- `make_client` lines 47–52 creates an in-memory app with a fake integration.
- `create_identity` lines 55–67 posts the common valid identity fixture.
- `issue_identity_certificate` lines 70–76 posts the common certificate fixture.
- `test_identity_registration_creates_audit_event` lines 79–89 verifies state and the first audit record.
- `test_certificate_issuance_returns_metadata_without_private_key` lines 92–112 verifies safe fields and confirms key material is not returned.
- `test_certificate_failure_creates_failure_audit_event` lines 115–124 proves an integration failure becomes an audited API failure.
- `test_quarantine_changes_state_and_creates_audit_event` lines 127–135 verifies lifecycle isolation.
- `test_allowed_action_is_executed_and_audited` lines 138–155 verifies allow-list plus fingerprint success and simulated completion.
- `test_unauthorized_action_is_denied_and_audited` lines 158–173 verifies that a valid identity still cannot exceed its policy.
- `test_high_risk_action_waits_for_and_accepts_operator_approval` lines 176–212 verifies pending state, approval transition, execution, and evidence.
- `test_certificate_renewal_retires_old_certificate` lines 215–226 verifies old/new lifecycle and current fingerprint replacement.
- `test_compromise_quarantines_revokes_and_recovers_with_replacement` lines 229–256 verifies the complete incident story and distinct replacement.
- `test_step_ca_revocation_uses_a_revoke_token` lines 259–282 injects a subprocess runner, checks the two-command revoke contract, and prevents a regression to the invalid CLI shape.

The fake client tests domain/API behavior quickly. The PowerShell scripts then prove the same contracts against Docker, real mounts, real step-ca, real SoftHSM, and the real browser proxy.

## 10. One request traced end to end

Trace `POST /identities/{id}/actions` as an exercise:

1. `src/App.tsx` calls `requestAction` only with a known identity, action, target, and displayed fingerprint.
2. `src/api.ts` serializes JSON and sends it to `/api/identities/{id}/actions`.
3. Vite rewrites `/api` away and sends the request to FastAPI.
4. `actions.py:request_action` obtains a session through `dependencies.py:get_session`.
5. Pydantic has already enforced field lengths; the route loads the ORM identity.
6. The route compares the certificate fingerprint before policy. This proves identity binding, not permission.
7. `policy/service.py:evaluate_action` checks status, allow-list, risk, and approval requirement.
8. The route writes an `ActionRequestRecord` and calls `AuditService.record`.
9. If allowed, the deterministic simulator returns a result; if high risk, the result stays empty until an operator approves.
10. SQLAlchemy commits the action and evidence together.
11. The JSON response returns to React, the action helper refreshes the eight-resource snapshot, and the policy panel/audit sequence changes.

That is the core Meridian distinction: a certificate can establish which identity presented itself; policy decides what that identity may do; audit makes the decision explainable later.

## 11. Files intentionally not hand-annotated

- `package-lock.json` is generated dependency resolution. Its important lesson is reproducibility, not the meaning of each transitive package line.
- `tsconfig*.json` are compiler contracts: strict source checking, browser libraries, no emitted app code, and a composite Vite config project.
- Empty package initializers contain no runtime behavior.
- Generated runtime folders, `node_modules`, `dist`, certificates, keys, token files, and databases are local evidence/cache and must stay ignored.

## 12. How to study actively

Start with `main.py`, then follow one endpoint rather than opening every file at once. Put a breakpoint or temporary log at the route, domain function, integration adapter, and audit service. Run one focused test, inspect the database row, and then run the matching Docker script. Finally use the dashboard to observe the same state transition. This moves from syntax to control flow to operational evidence—the same progression the earlier chapters use for cryptography and resilience.
