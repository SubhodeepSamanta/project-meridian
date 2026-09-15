# Certificate foundation

## Purpose

This milestone proves the smallest real PKI path before Meridian has an API or dashboard:

1. Docker starts a local `step-ca` authority.
2. `step-ca` creates a synthetic root CA and issuing CA.
3. The CA issues a short-lived test certificate.
4. OpenSSL inspects the certificate and verifies its chain to the root CA.

The repeatable command is:

```powershell
pwsh -File .\scripts\run_foundation.ps1
```

## What each part means

- The root CA is the top-level trust anchor for this local lab.
- The issuing CA signs the test certificate on behalf of the root.
- The test certificate binds the name `meridian-test` to a public key.
- The private key proves possession of that identity and is kept in ignored local runtime data.
- OpenSSL checks the certificate fields and verifies the root-to-issuing-CA-to-test-certificate chain.

## Local runtime

The Compose service uses the pinned `smallstep/step-ca:0.30.2` image and exposes the CA at `https://localhost:9000`. The CA data is bind-mounted under `infrastructure/step-ca/runtime`, which is excluded from Git.

The script creates a random local password in an ignored temporary file, passes it to `step ca init` through the mounted container filesystem, copies it to the CA's ignored password path, and removes the temporary file. The password is not passed as a command-line argument, printed, or committed. The script also does not print the private key.

## Security boundary and limitation

This milestone uses step-ca's normal local encrypted-key storage. It does not yet use SoftHSM2 or PKCS#11. The protected-key boundary is a later milestone and must use the CGO-enabled step-ca image and a locally configured SoftHSM2 token. SoftHSM2 will remain a software simulation, not a physical HSM.

## Verification evidence

The milestone is complete only when the script shows:

- the Compose health check reports `healthy`
- OpenSSL displays the test certificate subject, issuer, serial, validity dates, SHA-256 fingerprint, and SAN
- OpenSSL reports the certificate chain as `OK`
- the generated certificate and key exist only in the ignored runtime directory

## Observed verification

On 15 September 2026, the script completed successfully twice in succession. The checks confirmed:

- the pinned `step-ca` 0.30.2 container was healthy
- `step ca health` returned `ok`
- the certificate subject was `CN=meridian-test`
- the issuer was the Project Meridian issuing CA
- the certificate had the `meridian-test` DNS SAN and a 24-hour validity period
- OpenSSL reported the root-to-intermediate-to-test-certificate chain as `OK`
- the second run replaced the test artifact successfully
- the CA container logs contained no password or private-key output
- generated certificates, keys, CA secrets, and database files were ignored by Git

OpenSSL is not installed on the Windows host. The script runs it in a temporary Alpine container, keeping the host installation smaller while still using the required inspection tool.
