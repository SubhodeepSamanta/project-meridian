# System flows

## Healthy identity flow

~~~mermaid
sequenceDiagram
    participant O as Operator
    participant W as React dashboard
    participant M as Meridian API
    participant C as step-ca
    participant H as SoftHSM token
    participant S as Sample service

    O->>W: register service
    W->>M: create identity
    O->>W: request certificate
    W->>M: submit certificate request
    M->>C: request signed certificate
    C->>H: use protected CA signing key
    H-->>C: signing operation result
    C-->>M: certificate and metadata
    M->>M: write audit event
    M-->>W: active identity
    S->>S: establish mTLS
    S-->>M: health and connection result
~~~

## AI-agent action flow

~~~mermaid
sequenceDiagram
    participant A as AI agent
    participant M as Meridian API
    participant P as Policy evaluator
    participant O as Operator
    participant T as Target service
    participant L as Audit store

    A->>M: request named action with certificate
    M->>M: validate certificate and identity status
    M->>P: evaluate identity, action, target, and risk
    alt low-risk approved action
        P-->>M: allow
        M->>T: perform action
        M->>L: record allowed action
        M-->>A: success
    else high-risk action
        P-->>M: approval_required
        M->>O: request approval
        O-->>M: approve or deny
        M->>L: record decision
        M-->>A: decision
    else revoked or unauthorized identity
        P-->>M: deny
        M->>L: record denied action
        M-->>A: blocked
    end
~~~

## Compromise and recovery flow

~~~mermaid
flowchart TD
    Start[Identity active] --> Detect[Compromise or policy violation detected]
    Detect --> Quarantine[Mark identity quarantined]
    Quarantine --> Revoke[Revoke or disable certificate]
    Revoke --> Block[Reject mTLS and action requests]
    Block --> Review[Operator reviews incident]
    Review --> Replace[Issue replacement certificate]
    Replace --> Test[Run mTLS and policy tests]
    Test --> Recover[Mark identity recovered]
    Recover --> Audit[Store complete incident evidence]
~~~

## Certificate expiry flow

1. The API reads certificate metadata.
2. A certificate reaches the warning period.
3. The dashboard displays the warning.
4. The renewal job requests a new certificate.
5. The new certificate is tested before activation.
6. The old certificate is retired.
7. The result is written to the audit log.

## Failure scenarios

### Expired certificate

Expected result: the connection is rejected, the dashboard identifies the affected identity, renewal is requested, and recovery is recorded.

### Revoked certificate

Expected result: the identity cannot complete the protected request, and the incident timeline shows the revocation reason.

### HSM unavailable

Expected result: signing fails closed. No private key is exported. The API shows a clear error and records the event.

### Unauthorized action

Expected result: the action is denied before it reaches the target service.

### High-risk action

Expected result: the action pauses for explicit operator approval and records the decision.

## Human-readable state names

Use clear status labels in the interface:

- healthy
- expiring_soon
- expired
- revoked
- quarantined
- recovery_in_progress
- recovered
- protected
- unavailable

Avoid unexplained numerical status codes in the user interface.
