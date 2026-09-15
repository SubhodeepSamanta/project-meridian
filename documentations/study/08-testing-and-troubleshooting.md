# Study 08 — testing, rechecking, and troubleshooting

## Why the project tests more than code

Meridian crosses Windows, Docker Desktop, WSL2, Linux containers, a CA, a PKCS#11 library, SQLite, an API, and a browser. A unit test can pass while a volume mount or network namespace is wrong. The project therefore uses several concentric checks:

1. Syntax/import and type checks catch broken module boundaries.
2. Deterministic API tests use a fake CA to exercise decisions and failure branches quickly.
3. Real-container checks use the actual `step` CLI, CA, database, mounts, and network.
4. Repeatable scripts check the complete vertical slices.
5. The frontend build and HTTP proxy smoke test check the browser delivery path.

## The one-command recheck

From the project root:

`pwsh -File .\scripts\run_all_checks.ps1`

The script validates Compose configuration, reruns the foundation, mTLS, API, policy, SoftHSM, and incident scenarios, builds the React dashboard, starts API/web services, and checks the frontend proxy. It ends with `FULL_STACK_CHECKS: PASS` and leaves local services running.

## Useful focused commands

- CA foundation: `pwsh -File .\scripts\run_foundation.ps1`
- service mTLS: `pwsh -File .\scripts\run_mtls.ps1`
- API tests: `docker compose run --rm --no-deps meridian-api pytest -q`
- policy/approval: `pwsh -File .\scripts\run_policy.ps1`
- SoftHSM/PKCS#11: `pwsh -File .\scripts\run_hsm.ps1`
- incident/recovery: `pwsh -File .\scripts\run_incident.ps1`
- frontend build: `Set-Location .\apps\web; npm run build`
- service inventory: `docker compose ps`
- recent logs: `docker compose logs --tail=100 <service-name>`

## Bug ledger

### Docker was initially unavailable

The project could not start while Docker Desktop was stopped. We checked Docker Desktop, WSL2, and the engine explicitly. Once Docker was running, `docker run hello-world` proved the engine path before building the project.

### step-ca initialization used mismatched passwords

The first automatic initialization path generated separate CA/provisioner password state and the script then saw `failed to decrypt JWE: invalid password`. It also made log handling unsafe for a teaching project. The fix was manual initialization with one random in-memory bootstrap password, a temporary ignored file, immediate move to the ignored runtime secret path, and removal of the temporary file. No password value was copied into documentation or output.

### Certificate validity exceeded the CA maximum

The mTLS script first requested `168h` while the configured CA allowed only `24h`. We fixed the caller to request `24h` instead of weakening the CA policy. The lesson is to fix the contract mismatch at the boundary and keep the shortest useful lifetime.

### The negative mTLS test was too weak

An initial no-client test only wrapped a socket. TLS failure can surface when application bytes are sent or read, so that test falsely passed. The corrected test sends an HTTP request and reads a byte, then accepts the expected connection or TLS failure shape.

### API import and serialization defects

A stale `Request` annotation caused test collection to fail with `NameError`. An identity detail route also tried to serialize SQLAlchemy `__dict__`, which would expose ORM internals. The fix was explicit safe-field mapping and Docker test collection after every rebuild.

### SQLite schema and evidence defects

The audit sequence was made explicit because a non-primary integer column should not be assumed to auto-increment. Later, adding `result_payload` exposed that `Base.metadata.create_all()` does not alter existing SQLite tables. A small startup migration adds the missing field while preserving synthetic evidence. This is why persistent-state checks matter alongside fresh in-memory tests.

### Policy live test found stale persistent state

The in-memory policy tests passed, but the first live request returned 500 because the persistent API database predated the new action column. Reading the API container traceback identified the exact table/column mismatch. The migration was added, the image recreated, and the same live scenario passed.

### HSM token probe matched the wrong text

The first SoftHSM run searched for `meridian-hsm` anywhere in slot output. Docker's generated container name also contained that text, so token initialization was skipped and PKCS#11 reported `could not find PKCS#11 token`. The failed generated runtime was archived, and the probe now matches the `Label:` field.

### CA revocation used the wrong CLI contract

The first live compromise run passed issuance flags to `step ca revoke`; the CLI reported too many positional arguments. Official command usage showed that revocation needs a short-lived `step ca token --revoke` followed by `step ca revoke --token`. The adapter now does that and converts legacy hexadecimal serial inventory values to the decimal form expected by the CLI.

### PowerShell array matching caused a false HSM failure

The PKCS#11 object listing contained both expected key labels, but PowerShell applied `-notmatch` element-by-element and returned nonmatching lines as a truthy array. Joining output into one string fixed the assertion. The full suite then passed.

### Frontend type and network namespace defects

The first TypeScript build lacked `@types/react`, `@types/react-dom`, and `@types/node`. Explicit declarations fixed the build. The first Compose browser proxy used `localhost:8000` from inside the web container and returned `ECONNREFUSED`; Compose now sets `VITE_API_TARGET=http://meridian-api:8000` while host development keeps the localhost default.

### Browser visual helper unavailable

The required CUA browser helper reported a missing kernel-assets path twice, so no screenshot was claimed as inspected. Build, HTTP, proxy, and service checks still passed. A human visual/accessibility review remains appropriate before treating the design as production UI.

## Troubleshooting order

1. Run `docker version` and `docker compose version`.
2. Run `docker compose config --quiet`.
3. Check `docker compose ps` for state and health.
4. Check the specific service logs without printing secret files.
5. Re-run the smallest failing script.
6. Re-run `run_all_checks.ps1` after the fix.
7. Inspect `git status --short --ignored` to ensure generated runtime is not tracked.

Do not “fix” a failed test by weakening the CA lifetime, accepting missing client certificates, exporting private keys, or replacing a real failure with a fake success message.
