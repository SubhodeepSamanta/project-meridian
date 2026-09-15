# Study 04 — identity proof, policy, and approval

## The central idea

Authentication answers “who is this?” Authorization answers “what may this identity do?” A certificate is evidence for the first question. It must not become an automatic answer to the second.

Meridian makes this visible with two deterministic agents:

- Agent Alpha owns `read_status` and `rotate_certificate`.
- Agent Beta owns only `read_status`.

Both have separate registered identities and short-lived certificates. The same policy engine treats their authority separately.

## How the decision works

1. The API finds the registered identity.
2. The presented certificate fingerprint must match the identity's current fingerprint.
3. The identity must be active.
4. The action must appear in its explicit allow-list.
5. The action receives a risk classification.
6. Low/medium allowed actions execute in the simulator.
7. Allowed high-risk actions become pending until an operator approves or denies them.
8. The decision and reason are recorded in the audit chain.

The order matters. Checking the certificate before policy prevents an identity from borrowing another identity's authority. Checking lifecycle state before execution makes quarantine and revocation meaningful.

## Why the allow-list is explicit

An identity with no matching rule should fail closed. The engine does not infer permission from an action name, agent kind, owner, or certificate existence. The policy is stored as the identity's named action list so a learner can inspect the cause of every decision.

## Why high-risk approval is separate

A high-risk action can be legitimate and still deserve human review. `approval_required` is not a failure and is not permission. It is a pause in the state machine:

```text
requested -> approval_required/pending -> approved/allow -> executed
                                  \-> denied/deny
```

The pending request is persisted before approval. Restarting the API does not silently turn it into permission.

## Commands used

Run the complete demo:

```powershell
pwsh -File .\scripts\run_policy.ps1
```

The script uses `Invoke-RestMethod` to create identities, obtain certificates, submit action requests, and approve the high-risk action. It checks the returned decisions and exits nonzero if any state is wrong.

Run automated tests:

```powershell
docker compose build meridian-api
docker compose run --rm --no-deps meridian-api pytest -q
```

## Problems found and fixed

The first live policy run failed even though the unit tests passed. The existing SQLite file had been created before `result_payload` was added, and `Base.metadata.create_all()` does not modify existing tables. The traceback showed `table action_requests has no column named result_payload`. We added a small, backward-compatible startup migration for the local SQLite POC, rebuilt the image, and repeated the live scenario successfully.

This is an important testing lesson: in-memory tests verify code behavior on a fresh schema; a persistent-container test verifies upgrades and old local state.

## Limits

The current endpoint receives a fingerprint in the JSON body, so it demonstrates the relationship but does not yet extract identity from a real mTLS connection or signed request. The action target is simulated. API authentication, richer policy composition, operator identity, and real service execution are future hardening steps.
