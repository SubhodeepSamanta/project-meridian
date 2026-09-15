# Protected-key boundary milestone

## What was built

Meridian now has a separate HSM-backed CA simulation in the `hsm-ca` Compose service:

- `smallstep/step-ca:hsm` supplies the CGO-enabled CA and `step-kms-plugin`.
- Debian packages supply SoftHSM2 and `pkcs11-tool`.
- SoftHSM stores the synthetic root and intermediate private keys in a token database.
- The CA configuration points its intermediate signing key at a PKCS#11 URI.
- The CA issues a short-lived test certificate through that signing path.
- The test temporarily removes the token directory and confirms that the CA stops/fails closed.

This is deliberately separate from the normal disk-encrypted `step-ca` service so the existing foundation and mTLS demo remain easy to compare with the protected-key path.

## Verification

Run the repeatable milestone:

```powershell
pwsh -File .\scripts\run_hsm.ps1
```

Expected result:

```text
HSM_SIGNING_PATH: PASS
NO_DISK_CA_KEY: PASS
TOKEN_UNAVAILABLE: EXPECTED_FAILURE
Protected-key boundary milestone passed.
```

The script also lists the two expected PKCS#11 key objects, verifies the resulting CA is healthy after restoration, and leaves the generated token and certificates under ignored local runtime state.

## Configuration shape

The important conceptual configuration is:

```json
{
  "key": "pkcs11:id=7332;object=meridian-hsm-intermediate",
  "kms": {
    "type": "pkcs11",
    "uri": "pkcs11:module-path=/usr/lib/softhsm/libsofthsm2.so;token=meridian-hsm?pin-source=/home/step/secrets/hsm-pin"
  }
}
```

The module path points to the PKCS#11 shared library, `token` selects the token label, and `pin-source` keeps the PIN out of the configuration string and command output. The actual local runtime file is ignored and never committed.

## Official design reference

The implementation follows Smallstep's documented requirement for a CGO build for PKCS#11, its `step-ca:hsm` image guidance, and the documented SoftHSM PKCS#11 URI shape: [Smallstep cryptographic key protection](https://smallstep.com/docs/step-ca/cryptographic-protection/). The CA still uses established PKI tooling; Meridian does not implement signing or PKCS#11 itself.

## Important limitation

SoftHSMv2 is a software implementation of a PKCS#11 interface, not a physical HSM. It demonstrates the API boundary, object naming, protected-key workflow, and fail-closed behavior. It does not provide the tamper resistance, independent hardware boundary, operational controls, or certification of a real HSM. The local token files are synthetic lab state and should not be treated as protected production secrets.

The HSM CA's JWK provisioner password remains a local ignored file because this is a self-contained POC. A production design would use a proper secret-management and operator-authentication path.

## Problem found and fixed

The first run falsely believed the token existed because the slot probe searched for the text `meridian-hsm`, which also appeared in Docker's generated container name. The probe now matches the SoftHSM `Label:` field exactly. The failed generated runtime was archived under `.local/archive` rather than overwritten, and the corrected run created real root/intermediate objects and passed certificate issuance.
