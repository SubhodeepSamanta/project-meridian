# Architecture

## Architectural principle

Use established PKI software for cryptographic operations. Meridian owns the demonstration workflow, inventory, policy decisions, incident state, audit events, and user interface. It does not invent a certificate authority or cryptographic protocol.

## Logical components

### React web application

Displays identities, certificates, policies, incidents, events, health, and the guided demonstration. It calls the API and contains no private keys.

### Meridian API

The Python service that coordinates identities, certificate requests, policy decisions, incident actions, audit events, and simulation controls.

### Certificate integration

An adapter talks to step-ca using its supported command-line or API interface. The adapter is the only application boundary that knows how certificate issuance and renewal are requested.

### PKCS#11 integration

The protected-key adapter represents the HSM boundary. During local development it connects to SoftHSM2. The rest of the application should depend on a small interface, not on SoftHSM-specific details.

### Sample services

Small local HTTPS services that require client certificates. They demonstrate successful mTLS, failed access after revocation, and recovery after replacement.

### Agent simulator

Two or three deterministic Python processes that request named actions. Each agent has an owner, purpose, certificate, and policy. The first release does not need an external language model.

### Policy layer

Evaluates identity, requested action, target, risk level, and approval state. It returns allow, deny, or approval_required with a reason.

### Audit store

Stores structured events such as certificate_issued, action_allowed, action_denied, identity_revoked, certificate_replaced, and recovery_completed.

## High-level diagram

~~~mermaid
flowchart LR
    User[Operator] --> Web[React dashboard]
    Web --> API[Meridian API]
    API --> DB[(SQLite audit and inventory)]
    API --> CA[step-ca issuing CA]
    CA --> Token[SoftHSM2 PKCS#11 token]
    API --> Policy[Policy evaluator]
    API --> Services[Sample HTTPS services]
    Agent1[Agent Alpha] --> API
    Agent2[Agent Beta] --> API
    Services --> CA
    API --> Events[Incident and audit events]
    Events --> DB
    DB --> Web
~~~

## Trust boundaries

1. The browser is untrusted with respect to private keys.
2. The API is the workflow coordinator but should not export CA private keys.
3. step-ca is the certificate authority boundary.
4. SoftHSM is the protected-key boundary in the lab.
5. Sample services and agents are untrusted workloads.
6. The database contains test metadata and events, not production secrets.

## Domain model

### Identity

- id
- name
- kind: service or agent
- owner
- purpose
- status: active, suspended, revoked, quarantined
- certificate fingerprint
- created_at

### Certificate

- id
- identity_id
- serial_number
- subject
- issuer
- not_before
- not_after
- status
- key_algorithm
- renewal_status

### Action request

- id
- identity_id
- action
- target
- risk_level
- approval_status
- decision
- reason
- requested_at

### Audit event

- id
- event_type
- actor
- subject
- result
- reason
- correlation_id
- timestamp
- event_hash

## Important design decision

The MVP should use a modular monolith for the Meridian API, not microservices. The sample services, CA, and token are separate containers because they represent real trust boundaries. The application code remains easy to read and run.
