# Mutual TLS foundation

## Purpose

This milestone adds two local HTTPS services and proves that both sides of a connection participate in certificate authentication:

- `service-a` listens on port 9443.
- `service-b` listens on port 9444.
- each service has a certificate issued by the Meridian issuing CA
- each service trusts the Meridian root CA
- each service requires a client certificate
- a certificate-authenticated peer call succeeds
- a client without a certificate is rejected

Run the repeatable check from the project root:

```powershell
pwsh -NoProfile -File .\scripts\run_mtls.ps1
```

## Implementation boundary

The services are intentionally small Python HTTPS processes in `simulators/services/service.py`. They do not contain Meridian policy logic. They only demonstrate the transport identity layer. The backend will own authorization decisions in a later milestone.

The service containers receive only the root certificate and their own service certificate/key. They do not receive the CA private keys, CA database, or CA password.

## Verification

The script proves:

1. the CA foundation remains healthy
2. service certificates can be issued through the CA
3. both service processes run
4. `service-a` can call `service-b` using its certificate
5. a client that has the root certificate but no client certificate cannot complete the protected request
