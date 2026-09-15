# Study 09 — advanced topics and honest limits

## Trust boundaries

Meridian separates the browser, API, CA, SoftHSM token, services, agents, and database. Each boundary asks what data may cross it. The browser gets metadata and decisions. The API gets provisioner access but not CA signing-key files. The CA uses the PKCS#11 boundary for the HSM simulation. Services and agents are workloads whose identity and authority can be revoked.

This is a reference architecture for learning, not a threat-model completion certificate. A real threat model would name assets, adversaries, trust assumptions, attack paths, controls, residual risk, and evidence owners.

## Passive versus active revocation

The local `step-ca` path demonstrates certificate revocation and refusal to continue a compromised identity's workflow. The sample services do not yet query OCSP or a distributed CRL on every handshake. With short-lived certificates, passive revocation limits future renewal, while immediate active blocking needs a client-side or gateway-side status check. The demo exposes this distinction rather than implying that a database status change instantly changes every already-established TLS connection.

## Certificate and identity are different objects

An identity can receive multiple certificates over time. Renewal retires the old credential normally. Compromise revokes the old credential and requires a quarantined recovery flow before replacement. The identity record owns business context; the certificate record owns validity and key metadata.

## Crypto-agility intuition

Crypto-agility is the ability to change algorithms, key sizes, curves, signature suites, or trust chains without rebuilding every consumer. Meridian already moves in that direction by keeping certificate issuance behind `StepCaClient`, storing key algorithm metadata, using short-lived credentials, and representing trust relationships in the dashboard.

A future migration scenario should issue a second algorithm profile, run compatibility tests, dual-publish trust roots where appropriate, monitor remaining old certificates, and retire the old profile after evidence. It should not invent a custom cipher or silently switch algorithms during an incident.

## Protected-key scaling

SoftHSM proves PKCS#11 integration semantics and fail-closed behavior. A real deployment would need hardware or managed HSMs, dual control, key backup/restore, operator separation, PIN custody, availability design, audit integration, and a tested disaster-recovery plan. The private key non-extractability flag shown by `pkcs11-tool` in this lab is a software-token attribute, not physical tamper resistance.

## Concurrency and storage

The API's `max(sequence) + 1` audit allocation is understandable for a single-process SQLite teaching POC. It is not safe as a high-concurrency global sequence. A production store would use a database sequence/transaction strategy, append-only controls, independent retention, and external integrity verification. SQLite itself is a deliberate local constraint.

## API security still to add

The POC has no login, operator identity, role-based authorization, rate limiting, request signatures, mTLS at the API boundary, or external secret manager. The fingerprint in the action JSON demonstrates the relationship between credential and identity; it is not a substitute for transport-bound client-certificate verification. These are explicit next hardening steps.

## Reusable teaching pattern

For any new feature, ask five questions:

1. What establishes identity?
2. What establishes authority?
3. What happens when the dependency is unavailable?
4. What evidence proves the decision?
5. What is the safe recovery path?

That pattern keeps “who,” “what,” “failure,” “evidence,” and “recovery” connected as the platform grows.
