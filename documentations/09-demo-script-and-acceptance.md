# Demo script and acceptance criteria

## Demo goal

In five minutes, show that Meridian can create trusted identities, protect the issuing key, enforce access decisions, respond to compromise, and produce evidence.

## Demo preparation

- reset the local lab
- start all containers
- verify CA and token health
- open the dashboard
- confirm that all generated identities are synthetic
- keep the terminal available only for a fallback view

## Demo script

### 1. Start healthy

Show the overview:

- two services healthy
- two agents active
- issuing CA available
- protected signing token available
- no open incidents

### 2. Inspect identities

Open an agent:

- owner
- purpose
- certificate fingerprint
- expiry time
- allowed actions
- current status

Explain that the certificate is the agent’s machine identity, not proof that the agent is trustworthy by itself.

### 3. Perform an allowed action

Run a low-risk action. Show:

- certificate accepted
- policy allowed
- target service responded
- audit event created

### 4. Block an unauthorized action

Ask the same agent to perform an action outside its policy. Show:

- request denied
- target service was not called
- reason displayed
- audit event created

### 5. Simulate compromise

Mark the agent compromised. Show:

- identity becomes quarantined
- certificate is revoked or disabled
- later requests fail
- mTLS access is rejected

### 6. Recover

Approve replacement. Show:

- new certificate issued
- old identity remains in the incident history
- new identity passes the mTLS test
- recovery event is recorded

### 7. Demonstrate protected signing

Temporarily make the SoftHSM token unavailable. Show:

- issuance fails closed
- no private key appears in the API response or logs
- the incident is recorded
- the token can be restored and the workflow retried

## Acceptance criteria

### Identity

- identities have stable IDs and clear statuses
- service and agent identities are visually distinguishable
- identity ownership and purpose are visible

### Certificates

- certificates can be issued from the configured CA
- expiry is displayed correctly
- renewal creates a new certificate
- revoked or disabled identity cannot complete the protected flow

### mTLS

- a valid certificate succeeds
- an invalid, expired, or revoked certificate fails
- failure is visible in the dashboard and audit trail

### Policy

- an allowed action succeeds
- an unauthorized action is denied before reaching the target
- a high-risk action requires explicit approval

### HSM boundary

- the lab uses a PKCS#11-compatible token path
- key material is not returned by API endpoints
- unavailable token behavior fails closed
- SoftHSM limitations are visible in documentation

### Audit

- every issuance, decision, revocation, replacement, and failure creates an event
- event records include timestamp, actor, subject, result, and reason
- incident events can be viewed in order

### Usability

- a new user can start the project using the setup guide
- the main demonstration can be reset and repeated
- the dashboard explains errors in plain language

## Evidence to deliver

- source repository
- architecture diagram
- threat model
- API documentation
- test results
- demo recording
- one-page project brief
- limitations and future-work document
