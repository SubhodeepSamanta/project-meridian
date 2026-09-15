# Scope and requirements

## Minimum viable product

The MVP contains one local trust domain with:

- one offline root CA represented by the lab setup
- one online issuing CA
- one PKCS#11-compatible software token for the issuing key
- two sample services
- two simulated AI agents
- short-lived X.509 certificates
- mutual TLS between services
- a small policy engine
- an audit event store
- a React dashboard
- controlled failure and recovery scenarios

## Core user stories

### Identity operator

As an identity operator, I can create or register a service or AI agent and see its owner, purpose, certificate, status, and allowed actions.

### Service owner

As a service owner, I can request a certificate, use it for mTLS, renew it, and see when it will expire.

### Security operator

As a security operator, I can revoke an identity, immediately block its access, record the reason, and issue a replacement identity through an approved process.

### Auditor

As an auditor, I can inspect a chronological record of certificate issuance, use, policy decisions, revocation, replacement, and recovery.

### Demonstration user

As a demonstration user, I can run a guided incident scenario and see the system move from healthy to compromised to recovered.

## In scope for MVP

- identity registration
- certificate issuance through step-ca
- certificate metadata display
- certificate expiry detection
- certificate renewal
- certificate revocation or passive revocation demonstration
- service-to-service mTLS
- agent identity represented by a certificate
- action authorization using simple policy rules
- approval state for high-risk actions
- identity quarantine
- replacement certificate issuance
- append-only audit events
- incident timeline
- dashboard health states
- repeatable demo scripts
- automated backend tests

## Out of scope for MVP

- public Internet certificates
- real customer systems
- real production HSMs
- multi-tenant SaaS
- SSO and enterprise directory integration
- Kubernetes deployment
- full OCSP or enterprise revocation infrastructure
- complete certificate discovery across an organization
- a commercial-grade certificate lifecycle manager
- custom cryptographic algorithms
- a general-purpose AI assistant
- real autonomous agents with unrestricted tools
- a claim of FIPS validation or production security certification

## Priority order

If time becomes limited, preserve features in this order:

1. certificate issuance
2. mTLS
3. revocation and blocking
4. replacement and recovery
5. audit timeline
6. HSM-compatible key protection
7. React dashboard polish
8. policy and approval flow
9. AI-agent scenario
10. crypto-agility extension

## Risk boundaries

The application must never:

- use real private keys
- connect to a customer CA or HSM
- send certificate material to an external AI service
- store secrets in source control
- imply that SoftHSM is equivalent to a physical HSM
- silently approve high-risk actions
- hide failed certificate or policy checks
