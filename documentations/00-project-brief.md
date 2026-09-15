# Project Meridian project brief

## One-sentence definition

Project Meridian is a local digital-trust platform that gives services and AI agents cryptographic identities, protects important keys, limits what identities can do, records activity, and demonstrates safe response to compromise and failure.

## The problem

Organizations depend on certificates and private keys for secure communication. A certificate may expire, a key may be mishandled, an identity may be compromised, or a trust chain may need to change. If nobody can quickly understand the impact and recover safely, services can stop or unauthorized access can continue.

Meridian makes these situations visible and testable in a safe local environment.

## What Meridian demonstrates

1. A trusted certificate authority issues identities.
2. A service or AI agent uses its certificate to authenticate.
3. A protected key store keeps the important CA key away from ordinary files.
4. Policy decides which actions an identity may request.
5. Every important action produces an audit event.
6. A compromised or expired identity can be revoked and replaced.
7. Operators can see the impact and recovery path in a React dashboard.

## Target audience

- PKI and cryptography consultants
- security architects
- certificate and HSM operations teams
- engineering teams building internal platforms
- people evaluating secure AI-agent identity

## Why this is relevant to Encryption Consulting

The public company material covers PKIaaS, HSMaaS, certificate lifecycle management, cryptographic inventory, crypto-agility, and AI-agent identity. Meridian is designed as a small reference implementation and customer proof-of-value around those themes. It must complement those capabilities rather than claim to replace them.

This alignment is an evidence-based hypothesis from public sources, not a claim about the company’s private roadmap.

## Product promise

Meridian should make a difficult security story understandable in a few minutes:

> An identity is issued, used, monitored, challenged, revoked, replaced, and audited without exposing the protected private key.

## Success definition

The first release is successful when a new user can start the system locally, understand the architecture, run the complete incident demo, inspect the resulting evidence, and explain what each PKI component does.

## Deliberate limitations

- The first release is local only.
- All users, services, agents, certificates, and events are synthetic.
- SoftHSM is a software test token, not a physical or certified HSM.
- The system is not approved for production keys or customer data.
- Meridian will not implement cryptographic algorithms or a new CA from scratch.
- An AI model is optional. The first agents can be deterministic Python services.
