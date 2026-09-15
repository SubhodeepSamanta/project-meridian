# Policy and agent-action milestone

## Purpose

Meridian now distinguishes identity proof from authorization. A certificate fingerprint matching the registered identity proves which identity made a request. The policy engine then decides whether that identity may perform the named action against the named target.

## Behavior

- Every action request includes an identity, action, target, and presented certificate fingerprint.
- A mismatched fingerprint is denied and audited.
- An inactive, quarantined, suspended, or revoked identity is denied.
- An action not in the identity allow-list is denied.
- Allowed low- and medium-risk actions execute through a deterministic local simulator.
- Allowed high-risk actions enter `approval_required` / `pending` and do not execute.
- An operator can approve or deny a pending high-risk action.
- Every decision is written to the hash-linked audit stream.

## Risk model

The POC classifies `delete_data`, `revoke_identity`, `rotate_certificate`, and `rotate_trust_chain` as high risk. `send_message` and `update_configuration` are medium risk. Unknown actions default to low risk, but still require an explicit allow-list entry. This classification is intentionally simple and visible; it is a teaching policy, not an enterprise policy language.

## Verification

Run the repeatable scenario:

```powershell
pwsh -File .\scripts\run_policy.ps1
```

The script creates unique synthetic names on each run, so no existing local rows are overwritten. The successful result contains:

```text
ALLOWED_ACTION: PASS
UNAUTHORIZED_ACTION: EXPECTED_DENIAL
HIGH_RISK_APPROVAL: PASS
Policy and agent milestone passed.
```

The API tests also run inside Docker:

```powershell
docker compose run --rm --no-deps meridian-api pytest -q
```

## Security boundary and limitation

The action executor is deliberately a deterministic simulator. It does not call an external service or perform destructive work. The certificate fingerprint check is useful for teaching the relationship between credential and identity, but it is not a complete TLS client-certificate verification layer. A later integration should validate the presented certificate chain, revocation state, and request binding at the transport or gateway boundary.
