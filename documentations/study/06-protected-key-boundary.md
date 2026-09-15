# Study 06 — PKCS#11 and the protected-key boundary

## From disk key to signing interface

In the normal foundation, `step-ca` has an encrypted private key file. Encryption protects the file at rest, but a running CA must eventually decrypt and use the key. A PKCS#11 design changes the interface: the CA asks a token to sign; it refers to a key object by URI instead of reading a PEM private key.

The important intuition is “the key operation moves to a boundary.” The CA still needs permission to use the key, but the application code does not receive the private key bytes as its normal input.

## What each component does

- SoftHSM2 provides a local software token and a PKCS#11 shared library.
- `step-kms-plugin` creates and accesses key objects through PKCS#11.
- `step-ca:hsm` is a CGO-enabled CA image that can call native PKCS#11 libraries.
- `pkcs11-tool` lets us inspect token slots and object metadata.
- `hsm-ca` is a separate Compose service so the learning comparison with disk-backed `step-ca` is explicit.

Smallstep documents that the standard `step-ca` binary does not support PKCS#11 and recommends a CGO build or the `step-ca:hsm` image. Its documented SoftHSM URI uses the module path, token label, and PIN source. Meridian follows that model: [official cryptographic protection guidance](https://smallstep.com/docs/step-ca/cryptographic-protection/).

## Build sequence

The setup script follows this order:

1. Build a pinned `step-ca:hsm`-based image with SoftHSM2.
2. Create a token labelled `meridian-hsm`.
3. Use `step kms create` to generate root and intermediate EC key objects inside the token.
4. Use `step certificate create` to create the root and intermediate certificates while the signing keys remain PKCS#11 objects.
5. Initialize a CA configuration for its provisioner and database.
6. Replace the config's intermediate `key` with the PKCS#11 object URI and add its `kms` configuration.
7. Remove the temporary disk CA-key files created by `step ca init`.
8. Start the CA and issue `hsm-test` through its HTTPS endpoint.

The temporary files from initialization are synthetic and are removed only after the HSM-backed configuration has been written. The resulting runtime contains certificates, provisioner metadata, and token files, but no root or intermediate CA private-key file.

## Commands used

Run the full setup and fail-closed test with `pwsh -File .\scripts\run_hsm.ps1`.

Inspect token objects with `docker compose exec -T hsm-ca sh -c 'pin=$(cat /home/step/secrets/hsm-pin); pkcs11-tool --module /usr/lib/softhsm/libsofthsm2.so --token-label meridian-hsm --login --pin "$pin" --list-objects'`.

Recheck health with `docker compose ps hsm-ca`.

## Fail-closed scenario

The script stops `hsm-ca`, moves the exact generated token directory to a temporary `.unavailable` name, starts the CA, and observes that the process does not remain running. It then restores the directory, starts the CA again, and leaves the final service healthy. No existing project data is deleted; the generated token directory is temporarily moved and restored.

This is the desired shape of a protected-key failure: issuance does not fall back to a disk key, export a private key, or silently continue with a different trust root.

## Problem and correction

The first run skipped token initialization because the text search matched the Compose container name rather than the token label. That produced `could not find PKCS#11 token` during `step kms create`. The failed runtime was archived for diagnosis, the probe was changed to match `Label: meridian-hsm`, and the complete setup was repeated successfully.

## What this does not prove

SoftHSM does not equal hardware security. The token database is still a file on the host, the PIN is a local ignored file, and the VM/container boundary is not a physical tamper-resistant device. The milestone proves integration semantics and safe failure behavior, not FIPS validation, production key custody, or resistance to a host administrator.
