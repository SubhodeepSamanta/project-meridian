# AI coding rules

These rules apply to every AI agent working on Meridian.

## Before coding

1. Read this file and the project brief.
2. Read the relevant architecture and flow document.
3. Check whether the requested feature is in scope.
4. Inspect the existing code before adding files.
5. State the files that will change and why.
6. Do not invent APIs, certificate behavior, standards, or company capabilities.
7. If a security behavior is uncertain, stop and ask for confirmation or research the official documentation.

## Implementation style

- prefer the simplest readable design
- use small modules with one clear responsibility
- keep the API, domain logic, integrations, and UI separate
- do not introduce microservices for ordinary application logic
- do not add a dependency when the standard library or existing dependency is sufficient
- do not create abstractions without a current use
- keep functions short and names specific
- make errors explicit and useful
- keep security decisions on the backend
- make all state changes auditable

## Security rules

- never implement cryptography manually
- never log private keys, passwords, tokens, or certificate contents that contain secrets
- never export a CA private key from the protected-key boundary
- fail closed when identity validation, policy evaluation, or key operations fail
- use synthetic identities and test certificates only
- make the SoftHSM limitation visible in documentation and the UI
- keep simulation controls local and clearly marked as demo controls
- do not connect to external infrastructure without explicit approval

## Comments

- write no comment unless it explains a non-obvious security or design decision
- comments must be short
- comments must be written in lowercase
- do not write comments that repeat the code
- do not write generated, promotional, or conversational comments
- do not use comments as a substitute for clear naming

Correct:

~~~python
# fail closed if the token cannot sign
~~~

Avoid:

~~~python
# this function checks if the certificate is valid
~~~

## Naming

- use certificate, identity, policy, incident, recovery, and audit vocabulary consistently
- avoid flashy names in code
- prefer get_identity over fetch_data
- prefer revoke_certificate over handle_security
- prefer ActionDecision over Result

## Testing

Every security behavior needs:

- a successful test
- a failure or denial test
- an audit-event test

At minimum, test:

- valid certificate
- expired certificate
- revoked certificate
- unauthorized action
- high-risk action awaiting approval
- replacement certificate
- unavailable signing token
- audit event creation

## Agent output format

When an AI agent finishes a task, it must report:

1. what changed
2. why it changed
3. files changed
4. tests run and their results
5. assumptions made
6. known limitations
7. any follow-up work

Do not report a feature as complete if it is only mocked, hard-coded, or visually represented without a working backend path.
