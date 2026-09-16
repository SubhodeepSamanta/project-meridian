# Study 07 — making trust visible

## Why a dashboard is part of the security system

Certificates, policy decisions, and incident state are difficult to reason about when they exist only as logs or database rows. The dashboard is a translation layer: it preserves the backend evidence while giving an operator a useful mental model.

The goal is not decoration. A good visual surface answers quickly:

- Is the trust domain healthy, including the protected signing boundary?
- Which identities exist, who owns them, and what are they for?
- Which credential is active, expiring, retired, or revoked?
- What is waiting for a human decision?
- What incident is open and what evidence proves recovery?

## Visual intuition

The topology is an orientation map, not a cryptographic graph. The center says “trust graph”; surrounding nodes represent the issuing CA, control API, agents, and mTLS services. Orbit rings suggest boundaries and relationships. The protected-key panel then names the real SoftHSM/PKCS#11 boundary and its live CA link. The identity registry and audit table carry the actual details.

The lifecycle track turns the platform into a story: observe the system, decide an action, contain compromise, and recover with a new credential. Its active state is derived from API evidence, so a running incident changes the story rather than triggering a fake animation.

## Component flow

```text
API snapshot (8 resources) -> React state -> derived metrics/story stage -> visual panels
      ^                                                  |
      +------- button action -> API mutation ------------+
```

The browser has no policy engine of its own. It requests an operation, renders the server's decision, and shows errors. The showcase button is a sequence of real API calls: register Alpha/Beta, issue their certificates, submit an allowed request, submit a denied request, and leave a high-risk request pending for an operator. This prevents a user from bypassing a deny decision by editing JavaScript in the browser.

## Commands used

Build locally from the web folder with `npm run build`.

Start the container with `docker compose up -d meridian-web` and open `http://127.0.0.1:5173`.

Check the proxy with `Invoke-RestMethod http://127.0.0.1:5173/api/health`.

Run `pwsh -File .\scripts\run_policy.ps1`, `pwsh -File .\scripts\run_hsm.ps1`, or `pwsh -File .\scripts\run_incident.ps1`, then refresh the page. The new events, identity states, approval gate, protected-boundary status, and incident theatre are real API data. The primary dashboard button runs the policy portion directly through the same API endpoints; HSM token removal stays in the explicit PowerShell workflow because it changes infrastructure state.

## Design choices

- React owns the components and state; Tailwind owns utility styling, focus rings, palette names, shadows, and responsive utility generation.
- A small bespoke CSS layer keeps the 3D topology inspectable without hiding perspective/transform rules inside a component library.
- The layout uses responsive grid rules and a reduced-motion media query.
- The visual language was deliberately refined toward an editorial operations console: graphite surfaces, ivory type, one signal-lime accent, amber risk, and red failure. It avoids noisy neon gradients and generic AI imagery while retaining purposeful 3D depth.
- Long lists remain readable through a recent/full audit toggle and compact identity metadata.
- The `Run the trust sequence` control creates unique Alpha/Beta names so demonstrations are repeatable without overwriting prior evidence.

## Problems and limits

The first Compose proxy was aimed at the wrong network namespace; this was found by calling `/api/health` through the browser server, not by looking at source alone. The CUA helper could not provide a screenshot because its kernel-assets path was missing, so automated visual inspection was unavailable in this environment. The build and HTTP smoke checks do not replace a human accessibility and visual review.

The current dashboard has no login, role-based UI, websocket stream, pagination, export report, or direct target-service response panel. Token removal is intentionally not a browser button: it is a destructive infrastructure mutation and remains in `run_hsm.ps1`. Those omissions are visible POC limits. The security decisions remain in the API and are audited there.
