# Tech stack and resources

## Chosen stack

### Frontend

- React
- TypeScript
- Vite
- plain CSS or small, local component styles
- browser fetch through one API client module

Do not add a large component library at the beginning. A clean dashboard with consistent cards, tables, status badges, and an incident timeline is enough.

### Backend

- Python
- FastAPI
- Pydantic models
- SQLAlchemy with SQLite
- pytest

The backend should be a modular monolith. Keep certificate operations, policy decisions, incidents, and audit events in separate domain modules.

### Security and identity tools

- step-ca for the lab certificate authority
- SoftHSM2 for a local PKCS#11-compatible software token
- OpenSSL for inspection and connection tests
- Python PKCS#11 adapter only behind a small internal interface

step-ca supports X.509 certificates, mTLS, short-lived certificates, renewal, and PKCS#11 integrations. The documentation also describes limitations that must be understood before making claims about enterprise behavior.

### Runtime and development

- Docker Desktop
- Docker Compose
- WSL2 on Windows if required by the local setup
- Git
- VS Code
- GitHub

## Container plan

The first compose file should contain:

- meridian-api
- meridian-web
- step-ca
- meridian-service-a
- meridian-service-b
- meridian-agent-alpha
- meridian-agent-beta

SoftHSM should be placed with the CA integration in the simplest safe arrangement. Do not create unnecessary containers just to make the architecture look large.

## Optional later tools

Only add these when the MVP is stable:

- Open Policy Agent for policy-as-code
- Playwright for browser testing
- Prometheus and Grafana for metrics
- OpenBao for a second key and secret-management comparison
- SPIFFE or SPIRE for workload identity comparison
- a local model such as Ollama for a genuine AI-agent demonstration

## Official resources

- [step-ca documentation](https://smallstep.com/docs/step-ca/)
- [step-ca ACME basics](https://smallstep.com/docs/step-ca/acme-basics/)
- [step-ca cryptographic protection](https://smallstep.com/docs/step-ca/cryptographic-protection/)
- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [Docker Compose documentation](https://docs.docker.com/compose/)
- [OpenSSL documentation](https://docs.openssl.org/)
- [SoftHSM project](https://www.softhsm.org/)
- [PKCS#11 standards at OASIS](https://www.oasis-open.org/standards/)
- [Open Policy Agent documentation](https://www.openpolicyagent.org/docs)
- [SPIFFE X.509-SVID specification](https://spiffe.io/docs/latest/spiffe-specs/x509-svid/)

## Learning order

1. X.509 certificates and certificate chains
2. public key and private key roles
3. certificate authorities and trust stores
4. TLS and mutual TLS
5. certificate renewal and revocation
6. PKCS#11 and HSM concepts
7. identity and authorization policy
8. audit evidence and incident response
9. crypto-agility and PQC migration

## Local setup requirements

Recommended:

- 8 GB RAM minimum, 16 GB preferred
- 30 GB free disk space
- Docker Desktop
- Python and Node.js
- Git

No cloud account, paid API, physical HSM, or customer data is required.
