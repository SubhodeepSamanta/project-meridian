# Study chapter 2: mutual TLS

## TLS before mutual TLS

TLS is a protected conversation. It gives a client three useful properties:

1. the conversation is encrypted
2. the client can authenticate the server
3. messages can be detected if they are changed in transit

Normal HTTPS is usually one-way identity: the server presents a certificate and the client verifies it. The client may be anonymous at the TLS layer.

Mutual TLS, or mTLS, adds the reverse direction. The server also asks the client for a certificate and verifies that certificate before accepting the connection. It is similar to a building where the visitor checks the building's identity card and the building checks the visitor's badge.

## What happens during the handshake

At a high level:

```text
service-a                         service-b
   | -------- client hello --------> |
   | <------- server certificate --- |
   | <------- request client cert -- |
   | -------- client certificate --> |
   | -------- proof of private key ->|
   | <------ encrypted application ->|
```

The private key is not sent. The client proves that it controls the private key corresponding to the public key in its certificate. The server checks the certificate chain against its configured trust root and then checks the proof.

## Why the root certificate is not enough

A client that merely possesses the Meridian root certificate can verify a server, but it cannot authenticate itself. The root certificate is public trust material. It is not a client credential.

The successful test loads:

- the Meridian root certificate as a trust anchor
- service-a's certificate
- service-a's private key

The negative test loads only the Meridian root certificate. It deliberately does not load a client certificate or private key. The server rejects the protected request.

## Service code intuition

`service.py` creates two different SSL contexts:

- the server context loads the service certificate and key, trusts the Meridian root, and sets `CERT_REQUIRED`
- the outgoing client context trusts the Meridian root and loads the service certificate and key

The HTTP routes are intentionally boring:

- `/health` returns the service name and the authenticated client common name
- `/call-peer` makes an mTLS request to the other service

That separation is useful. TLS proves transport identity; it does not decide whether a service is allowed to perform a business action. Meridian's future API and policy layer will make that decision.

## Commands used

The service certificate command runs inside the CA's Docker network. The full repeatable workflow is kept in `scripts/run_mtls.ps1` so a password or private key never needs to be pasted into a host terminal.

Start the two services after certificates exist:

```powershell
docker compose up -d service-a service-b
```

Run the complete milestone:

```powershell
pwsh -NoProfile -File .\scripts\run_mtls.ps1
```

The positive check is a Python HTTPS client inside `service-a`. It loads `service-a`'s certificate/key and calls `https://service-b:9444/health`.

The negative check is a temporary client container. It trusts the root but has no client credential, sends an HTTP request, and expects the server to close or reject the connection.

## Bugs and fixes

### Certificate lifetime mismatch

The first mTLS attempt requested 168 hours, but the freshly initialized CA authorizes a maximum duration of 24 hours. The CA correctly returned a forbidden response instead of issuing the certificate. The fix was to request 24 hours, matching the local CA policy, rather than silently changing the CA maximum.

### Weak negative test

The first no-client test only completed `wrap_socket()`. That returned before the server-side rejection was observed, so the test falsely treated the handshake as successful. The fix was to send an HTTP request and read one byte. A real response means the test must fail; a TLS error or closed connection is the expected result.

This is a general testing lesson: a test must observe the failure at the boundary the requirement names. “The socket wrapper returned” was weaker than “the protected request was rejected.”

## Evidence

The mTLS script passed after both fixes. The Docker Compose state showed both services running. The authenticated check printed `VALID_MTLS: PASS`. The certificate-less check printed `INVALID_MTLS: EXPECTED_FAILURE`.

## What mTLS does not prove

- It does not authorize every action a certificate holder requests.
- It does not prove that an AI agent is safe or truthful.
- It does not automatically implement revocation behavior in every TLS client.
- It does not remove the need for certificate expiry monitoring.
- It does not protect CA private keys with SoftHSM2; that is a later milestone.
