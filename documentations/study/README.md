# Project Meridian study guide

This folder teaches Project Meridian from first principles through the completed proof of concept. It is written for a reader who understands the idea of PKI but is still learning how the pieces behave in a real system.

Each chapter explains:

- what the concept means in ordinary language
- why Meridian needs it
- how the component works internally
- what files and commands implement it
- what result to expect
- how the result is verified
- what can go wrong and how the project handles failure
- what the design does not prove

The chapters are a living record. They are updated after each milestone from actual commands, test output, bugs, fixes, and design decisions. Generated keys, passwords, certificates, database files, and logs are never copied into these documents.

## Learning path

1. `01-foundation.md` — files, processes, Docker, certificates, trust, and the first CA
2. `02-mtls.md` — TLS, mutual TLS, certificate roles, and connection failures
3. `03-api-and-data.md` — the FastAPI modular monolith, SQLite, domain objects, and audit records
4. `04-policy-and-agent-identity.md` — identity, authority, policy, approval, and deterministic agents
5. `05-incidents-and-recovery.md` — expiry, quarantine, revocation, replacement, and recovery
6. `06-protected-key-boundary.md` — PKCS#11, SoftHSM2, signing, and fail-closed behavior
7. `07-dashboard-and-demo.md` — how the React dashboard turns security state into evidence
8. `08-testing-and-troubleshooting.md` — test strategy, repeatability, bugs, fixes, and verification
9. `09-advanced-topics.md` — trust boundaries, threat modeling, revocation limits, crypto-agility, and future work
10. `10-file-by-file-code-tour.md` — source-level walkthrough of every app, route, function, script, test, and frontend layer

## How to read commands

Commands are shown for Windows PowerShell from the project root:

```powershell
Set-Location 'C:\Users\USER\Desktop\Project Meridian'
```

Commands that run inside a container are labelled explicitly. A host command changes the Windows project or asks Docker to perform an operation. A container command runs inside the isolated lab environment. The distinction matters because a command can succeed in one environment while failing in another.

## Current status

All ten chapters are complete. The guide covers the implementation, actual verification commands, bugs and fixes, security boundaries, honest limitations, and a source-level file/function walkthrough.
