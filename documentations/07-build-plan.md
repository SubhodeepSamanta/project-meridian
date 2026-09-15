# Build plan

## Working method

Build one vertical slice at a time. Every slice must work from the React screen through the API and into the real local PKI tools.

Do not build a beautiful dashboard around fake data first. Build the security path first, then make it visible.

## Phase 0: project preparation

Deliverables:

- repository initialized
- documentations folder read
- README and .gitignore created
- Docker Desktop and WSL2 checked
- Python and Node.js checked
- scope accepted
- no real secrets or customer data

Exit condition: the project can be started from a clean machine using documented commands.

## Phase 1: certificate foundation

Deliverables:

- step-ca runs locally
- test root and issuing CA are configured
- a test service receives a certificate
- certificate metadata can be inspected
- generated files are excluded from Git

Exit condition: a repeatable script creates a test certificate and verifies its chain.

## Phase 2: service mTLS

Deliverables:

- two small HTTPS services run locally
- both trust the configured test CA
- the client certificate is required
- a valid client succeeds
- an invalid, expired, or wrong-issuer client fails

Exit condition: the mTLS success and failure tests pass without manual certificate copying.

## Phase 3: Meridian API

Deliverables:

- identity registration
- certificate inventory
- certificate status endpoint
- renewal request
- revoke or disable action
- audit event endpoint

Exit condition: API tests prove that every state change creates an audit event.

## Phase 4: protected key boundary

Deliverables:

- SoftHSM token is created locally
- PKCS#11 library is configured
- CA signing operation uses the protected-key path
- token-unavailable behavior fails closed
- no private key is returned by the API

Exit condition: a test proves that certificate issuance fails safely when the token is unavailable.

## Phase 5: agents and policy

Deliverables:

- Agent Alpha and Agent Beta have separate identities
- each agent has an owner, purpose, and allowed actions
- low-risk allowed action succeeds
- unauthorized action is denied
- high-risk action waits for approval
- every decision is audited

Exit condition: the same action produces the correct decision for allowed, denied, and approval-required cases.

## Phase 6: React dashboard

Deliverables:

- overview page
- identity list
- certificate details
- incident timeline
- policy decision view
- audit event view
- clear health and failure states

Exit condition: the full demo can be completed from the browser with no database editing.

## Phase 7: incident scenarios

Deliverables:

- certificate expiry simulation
- certificate revocation simulation
- identity quarantine
- certificate replacement
- HSM-unavailable simulation
- recovery verification
- downloadable or copyable incident report

Exit condition: the demo can be reset and repeated consistently.

## Phase 8: final polish

Deliverables:

- threat model
- architecture diagram
- API documentation
- setup guide
- test report
- limitations section
- short demo recording
- CEO-facing one-page brief

## Suggested weekly schedule

### Week 1

Learn the fundamentals and make step-ca issue one certificate.

### Week 2

Build two services and prove mTLS.

### Week 3

Create the API, identity model, certificate inventory, and audit events.

### Week 4

Integrate SoftHSM and implement safe failure behavior.

### Week 5

Add agents, policy, approval, revocation, and quarantine.

### Week 6

Build the React dashboard.

### Week 7

Add repeatable incident scenarios and recovery.

### Week 8

Test, simplify, document, and record the demo.

## Three-agent coordination

If three AI coding agents are used, divide work by boundaries:

### Agent one: backend and PKI

Owns the API, database, certificate integration, PKCS#11 boundary, and backend tests.

### Agent two: frontend

Owns React screens, components, API client, loading states, error states, and frontend tests.

### Agent three: research and quality

Owns official-source research, threat model, scenario definitions, documentation, test cases, and review of security claims.

Only one agent should change shared architecture or dependency decisions. All agents must read the documentation and report assumptions.
