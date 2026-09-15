# Research and decisions

## Research snapshot

- Research date: 15 September 2026
- Research basis: public company material, official standards, and official tool documentation
- Confidence rule: public information is not evidence of a private company roadmap

## Company alignment

Encryption Consulting publicly describes work and solutions involving:

- PKIaaS
- HSMaaS
- certificate lifecycle management
- certificate outage prevention
- cryptographic inventory and CBOM
- crypto-agility and PQC readiness
- AI-agent identity
- agent-to-agent mTLS
- CertSecure access through MCP

Useful public pages:

- [Encryption Consulting solutions](https://www.encryptionconsulting.com/solutions/)
- [PKIaaS](https://www.encryptionconsulting.com/pki-as-a-service/)
- [CertSecure Manager](https://www.encryptionconsulting.com/certificate-management-solution-certsecure-manager/)
- [CBOM Secure](https://www.encryptionconsulting.com/cryptographic-discovery-inventory/)
- [AI-agent identity](https://www.encryptionconsulting.com/solutions/ai-agent-identity/)
- [CertSecure MCP Server](https://www.encryptionconsulting.com/certsecure-mcp-server-agentic-ai-clm/)

## Why the project should not be a generic certificate manager

Certificate lifecycle management is already a mature commercial category. Meridian should therefore demonstrate a complementary problem:

- understanding identity dependencies
- testing failure and recovery
- proving protected-key behavior
- making policy decisions visible
- preserving incident evidence
- extending trust controls to AI-agent workloads

This is a product-positioning hypothesis, not a claim that Meridian is unique in the market.

## Standards and industry context

- [NIST crypto-agility guidance](https://csrc.nist.gov/pubs/cswp/39/upd1/considerations-for-achieving-crypto-agility/final)
- [NIST post-quantum cryptography project](https://csrc.nist.gov/projects/post-quantum-cryptography)
- [NIST software-agent identity concept paper](https://www.nist.gov/news-events/news/2026/02/new-concept-paper-identity-and-authority-software-agents)
- [CA/Browser Forum Baseline Requirements](https://cabforum.org/working-groups/server/baseline-requirements/requirements/)
- [MCP authorization specification](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization)
- [SPIFFE X.509-SVID specification](https://spiffe.io/docs/latest/spiffe-specs/x509-svid/)
- [OASIS PKCS#11 standards](https://www.oasis-open.org/standards/)

## Technical decisions

### Use step-ca instead of writing a CA

Reason: it provides an established local CA, X.509, mTLS, renewal, and documented integration points. Meridian should demonstrate orchestration and resilience, not invent certificate cryptography.

### Use SoftHSM2 for the first release

Reason: it is free and lets the project demonstrate the PKCS#11 boundary without buying hardware. Limitation: it is not a physical HSM and does not provide production hardware assurance.

### Use deterministic agents initially

Reason: the security value is identity, authorization, revocation, and evidence. A local language model is optional and should not hide whether the security controls work.

### Use a modular monolith

Reason: the system is a learning and demonstration project. Separate trust boundaries are represented by containers, while the Meridian application remains easy to read.

### Use React and TypeScript

Reason: a proper interactive dashboard will make invisible certificate and incident behavior understandable during a live demonstration.

## Claims Meridian must never make

- SoftHSM is a production HSM.
- Meridian is FIPS validated.
- Meridian replaces a commercial CLM.
- Meridian protects real customer environments.
- an AI agent is safe merely because it has a certificate.
- revocation behavior is universal across every TLS client.
- the project has been reviewed or endorsed by Encryption Consulting.

## Open questions for later

- Should the policy layer remain a small internal evaluator or move to OPA?
- Should a later version compare step-ca with OpenBao PKI?
- Should the project support SPIFFE or remain certificate-focused?
- Which real HSM interface would be used for an authorized enterprise integration?
- Which certificate and incident metrics matter most to a consulting engagement?
