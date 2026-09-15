# AI agent context

Paste the following context into an AI coding session when necessary. The files in this folder remain the authoritative source.

## Canonical project context

You are working on Project Meridian, a local proof of concept for digital-trust operations.

Meridian gives sample services and simulated AI agents cryptographic identities. It protects the issuing key through a PKCS#11-compatible software token, uses certificates for mTLS, evaluates action policy, records important events, and demonstrates revocation, quarantine, replacement, and recovery.

The frontend is React with TypeScript. The backend is Python with FastAPI. The database is SQLite. step-ca is the local certificate authority. SoftHSM2 is the local software token. OpenSSL is used for inspection and connection tests. Docker Compose runs the lab.

Meridian is not production software, not a commercial certificate manager, not a physical HSM, and not a new cryptographic implementation. All identities, certificates, keys, agents, actions, and events are synthetic.

## Required behavior

- certificate issuance must go through the configured CA integration
- important signing operations must remain behind the protected-key boundary
- security decisions must be made by the backend
- invalid, expired, revoked, quarantined, or unauthorized identities must fail closed
- every state-changing security operation must create an audit event
- high-risk actions must not be silently approved
- the dashboard must show the reason for a denial or failure
- all demonstration scenarios must be resettable and repeatable

## Required questions before changing code

1. Which documented requirement does this change implement?
2. Which domain owns the behavior?
3. Does the change cross a trust boundary?
4. What happens when the dependency is unavailable?
5. What audit event is created?
6. What test proves the success case?
7. What test proves the failure or denial case?
8. Does the change introduce a secret, external connection, or new dependency?

## Grounding rules

- use official documentation for step-ca, OpenSSL, PKCS#11, FastAPI, React, Docker, and security standards
- do not rely on a search-result summary for a security decision
- do not claim that a tool supports behavior unless its current documentation or a passing local test confirms it
- distinguish certificate revocation, certificate expiry, identity quarantine, and policy denial
- distinguish SoftHSM simulation from physical-HSM assurance
- distinguish an AI-agent identity from an AI-agent safety guarantee
- mark assumptions in code reviews and documentation

## Preferred task prompt

Implement [specific feature] for Project Meridian.

Before editing:

- read documentations/README.md
- read documentations/01-scope-and-requirements.md
- read the relevant architecture and flow documents
- inspect the current repository
- propose the smallest implementation and list files to change

During editing:

- follow documentations/06-ai-coding-rules.md
- keep the design readable and modular
- keep security decisions on the backend
- do not add unnecessary libraries
- do not add comments unless a non-obvious security decision needs one
- keep comments short and lowercase

After editing:

- run focused tests
- run the relevant build or type checks
- verify no secrets or generated certificates were added
- report changed files, tests, assumptions, limitations, and follow-up work
