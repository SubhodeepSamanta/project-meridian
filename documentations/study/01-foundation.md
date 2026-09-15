# Study chapter 1: the certificate foundation

## The problem in one sentence

Meridian needs a way for a service to prove, using mathematics performed by established software, that it owns a particular digital name. A certificate authority provides that starting point.

## Begin with the simplest intuition

Imagine a school issuing identity cards. The card contains a student's name and photo, and the school stamps it. A guard who trusts the school can inspect the card and decide whether to admit the student.

An X.509 certificate is a machine-readable identity card:

- the subject is the name being identified
- the public key is information others may share
- the issuer is the authority that signed the card
- the validity period says when the card is usable
- the signature lets a verifier detect tampering

The private key is the secret proof held by the identity owner. It must never be copied into an API response or printed in logs. The public key can be placed in the certificate because knowing it does not let somebody create the corresponding private-key signature.

## Why there are two CA certificates

Meridian uses a root CA and an issuing CA. The root is the trust anchor: an operator chooses to trust it. The issuing CA is the day-to-day signer. The test certificate is signed by the issuing CA, and the issuing CA is signed by the root.

This forms a chain:

```text
Project Meridian root CA
        |
        v
Project Meridian issuing CA
        |
        v
meridian-test certificate
```

OpenSSL can verify the chain by starting with the trusted root, accepting the issuing CA as an intermediate, and checking the test certificate's signature and validity.

## What Docker contributes

Docker gives the lab a repeatable process boundary. The host does not need a Windows installation of `step-ca` or OpenSSL for this milestone. Docker pulls the pinned `smallstep/step-ca` image, runs it as a CA process, and mounts its generated local state under the ignored runtime directory.

This is isolation for convenience and repeatability, not a complete security boundary. Docker Desktop and the host operating system still control the environment.

## Files created for the milestone

- `docker-compose.yml` describes the local CA container, port, mounted state, and health check.
- `scripts/run_foundation.ps1` starts the CA, issues the test certificate, and runs OpenSSL verification.
- `infrastructure/step-ca/runtime` holds generated local state and is ignored by Git.
- `README.md` gives the short setup path.
- `documentations/12-certificate-foundation.md` records the milestone contract and observed evidence.

## The important commands

Check that Docker can reach its engine:

```powershell
docker info
```

A successful result means the Docker client contacted the daemon. The foundation check used a disposable `hello-world` container first, which proved that Docker could pull an image, create a container, run it, and stream its output.

Validate the Compose file without starting it:

```powershell
docker compose config --quiet
```

Run the milestone:

```powershell
pwsh -NoProfile -File .\scripts\run_foundation.ps1
```

The script does four useful things:

1. Checks the Docker engine.
2. Initializes `step-ca` manually with one random local password for the CA and provisioner, without putting the password on the command line or in logs.
3. Waits for the CA health check, then requests a 24-hour `meridian-test` certificate through the CA's HTTPS API.
4. Mounts the generated state read-only into an Alpine container, installs OpenSSL there, prints safe certificate metadata, and verifies the chain.

Inspect only safe certificate fields:

```text
subject
issuer
serial
notBefore
notAfter
SHA-256 fingerprint
subject alternative name
```

The script intentionally does not print private-key contents or passwords.

## Why the script initializes the CA manually

The official Docker image can auto-initialize when environment variables are supplied. During testing, the image generated separate CA and provisioner passwords when no password was provided. The first version of the script incorrectly reused the CA password for the provisioner and the request failed with `failed to decrypt JWE: invalid password`.

The image entrypoint also prints its generated provisioner password during auto-initialization. That conflicts with Meridian's rule never to log passwords. The fixed script bypasses that auto-initialization path, creates one random password in an ignored temporary file, supplies it to both `step ca init` password-file options, copies the CA password to the expected ignored runtime path, and removes the temporary file.

This is a lesson in boundaries: a password file can be safe for a command while an image entrypoint can still accidentally disclose the same secret through logs. Both paths must be checked.

## Evidence from the completed run

The pinned `smallstep/step-ca:0.30.2` image started healthy. The CA health command returned `ok`. The issued certificate had `CN=meridian-test`, a `meridian-test` DNS SAN, the Project Meridian issuing CA as issuer, and a 24-hour lifetime. OpenSSL reported the chain as `OK`. Running the script a second time successfully reissued the test certificate.

The current runtime contains generated certificates, private keys, CA secrets, and database files. They are local synthetic data and are ignored by Git. The repository has no commit yet; this is intentional until the first coherent project snapshot is ready.

## What this milestone does not prove

- It does not prove mutual TLS; that is the next milestone.
- It does not use SoftHSM2 or PKCS#11.
- It does not protect a key with physical HSM assurance.
- It does not implement an authorization policy.
- It does not prove that an agent is safe because it has a certificate.
- It does not make the system production-ready.

## Source grounding

The workflow follows Smallstep's official Docker CA tutorial and command references. The official cryptographic-protection guidance distinguishes normal encrypted-on-disk keys from the CGO-enabled PKCS#11 path that will be studied later.
