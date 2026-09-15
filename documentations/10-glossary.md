# Glossary

## Certificate

A digital document that binds an identity to a public key and is signed by a trusted certificate authority.

## Certificate authority

A trusted system that issues and signs certificates.

## Certificate chain

The path from an end-entity certificate through an issuing CA to a trusted root CA.

## HSM

A hardware security module is a device designed to protect and use private keys. Meridian uses SoftHSM2 for local testing only.

## PKCS#11

A standard interface that lets software use cryptographic tokens and HSMs without depending on one vendor’s API.

## Private key

Secret cryptographic material used to prove identity or create signatures. It must be protected.

## Public key

Cryptographic material that can be shared and is placed in a certificate.

## mTLS

Mutual TLS. Both sides of a connection prove their identities with certificates.

## Revocation

Declaring that a certificate or identity must no longer be trusted.

## Quarantine

Temporarily isolating an identity so it cannot perform protected actions.

## Crypto-agility

The ability to change cryptographic algorithms, keys, or certificates without rebuilding the entire system.

## AI agent

A software process that can decide or request actions. In Meridian, an agent is treated as a workload with an identity and limited authority.

## Policy

Rules that decide whether an identity may perform a requested action.

## Audit event

A structured record of what happened, who or what caused it, what target was involved, and whether it succeeded.

## SoftHSM

A software implementation that behaves like a PKCS#11 cryptographic token for development and testing. It is not equivalent to a physical HSM.
