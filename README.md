# Project Meridian

Project Meridian is a local proof of concept for digital-trust operations. It uses synthetic services and simulated AI agents to demonstrate certificates, mutual TLS, authorization, protected key operations, incident response, and audit evidence.

This is learning and demonstration software. It is not a production certificate authority, commercial certificate manager, physical HSM, FIPS-validated system, or a place for real customer data or keys.

## Current status

The repository has completed the certificate foundation, service mTLS, API/data, policy/agent-action, protected-key-boundary, incident/recovery, React/Tailwind dashboard, verified audit evidence, study-guide, and final verification milestones. The web console uses Tailwind utilities plus a small authored CSS layer for its 3D trust topology, live protected-key panel, and editorial visual system.

## Run the foundation milestone

Requirements:

- Docker Desktop running
- Git
- Python 3.12
- PowerShell

From this directory, run:

```powershell
pwsh -File .\scripts\run_foundation.ps1
```

The script starts a local `step-ca` container, creates a synthetic root and issuing CA, requests a short-lived test certificate, and uses an isolated OpenSSL container to inspect the certificate and verify its chain.

To run the two-service mTLS milestone after the foundation is available:

```powershell
pwsh -File .\scripts\run_mtls.ps1
```

This issues synthetic certificates for `service-a` and `service-b`, starts both HTTPS services, and proves one authenticated call plus one certificate-less failure.

To run the API after the foundation is available:

```powershell
docker compose build meridian-api
docker compose up -d meridian-api
Invoke-RestMethod http://localhost:8000/health
```

For local backend development, create and use the Windows virtual environment:

```powershell
pwsh -File .\scripts\setup_backend_venv.ps1
pwsh -File .\scripts\run_backend_tests.ps1
```

The backend Docker image also installs its dependencies into `/opt/venv`; the container and local workflow therefore use isolated Python environments rather than a global interpreter.

The API stores local synthetic state under `.local/api`, which is ignored by Git.

To run the deterministic agent-policy demonstration:

```powershell
pwsh -File .\scripts\run_policy.ps1
```

It creates two synthetic agents, issues each a short-lived certificate, proves one allowed action, records one unauthorized denial, and pauses a high-risk action until explicit operator approval.

To run the protected-key boundary demonstration:

```powershell
pwsh -File .\scripts\run_hsm.ps1
```

It uses a SoftHSM2 token with the CGO-enabled `step-ca:hsm` image, verifies a certificate is issued through the PKCS#11 path, then verifies that token removal fails closed. SoftHSM is a software simulation, not a physical HSM.

To run the compromise and recovery demonstration:

```powershell
pwsh -File .\scripts\run_incident.ps1
```

It creates a synthetic agent, issues its original certificate, opens a compromise incident, quarantines and revokes the identity, then issues a distinct replacement certificate and records recovery.

The dashboard's `Run the trust sequence` button runs the policy portion directly through the API: it creates Alpha and Beta, issues both certificates, records Alpha's allowed request, records Beta's denied `delete_data` request, and leaves Alpha's `rotate_certificate` request waiting for the approval button. The dashboard also reports live `hsm-ca` reachability through the protected-boundary panel; token removal remains in `run_hsm.ps1` because it is an infrastructure mutation.

To rerun every milestone and the frontend build:

```powershell
pwsh -File .\scripts\run_all_checks.ps1
```

The final check leaves the local services running and ends with `FULL_STACK_CHECKS: PASS`.

Generated CA state and certificate files are stored under `infrastructure/step-ca/runtime` and are excluded from Git. Never place real keys, passwords, certificates, or customer data in this project.

## Documentation

The project documentation in `documentations` is the source of truth. Read it before changing the architecture or adding dependencies.
