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

The topology is now a real directed graph, but it is still not a cryptographic proof graph. SVG paths encode the live relationships between the protected HSM, issuing CA, Meridian control plane, API, agents, and services. Each node is a selectable button; selecting `AGENTS`, for example, highlights the two connected edges and changes the readout below the graph. The protected-key panel names the real SoftHSM/PKCS#11 boundary and its live CA link. The identity registry and audit table carry the actual details. The live execution panel is the bridge between the graph and the evidence: its counts and checkpoint states come from the same API snapshot, while the button briefly exposes the exact request phase during a run.

The lifecycle track turns the platform into a story: observe the system, decide an action, contain compromise, and recover with a new credential. Its active state is derived from API evidence, so a running incident changes the story rather than triggering a fake animation.

## Component flow

```text
API snapshot (8 resources) -> React state -> derived metrics/story stage -> visual panels
      ^                                                  |
      +------- button action -> API mutation ------------+
```

The browser has no policy engine of its own. It requests an operation, renders the server's decision, and shows errors. The showcase button is a sequence of real API calls: register Alpha/Beta, issue their certificates, submit an allowed request, submit a denied request, and leave a high-risk request pending for an operator. During those calls the interface moves through `registering`, `issuing`, `evaluating`, and `approval` phases. This prevents a user from bypassing a deny decision by editing JavaScript in the browser and gives the operator evidence that the button is doing work.

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
- Long lists remain readable through a recent/full audit toggle and a registry that foregrounds the newest twelve records while retaining the full total.
- The selected identity is rendered as a certificate dossier instead of a single tiny fingerprint line. The dossier teaches the safe certificate fields—issuer, algorithm, serial, expiry, and public fingerprint—without exposing a private key.
- Incident theatre names the containment goal directly as “isolate the unknown” and visualizes the lifecycle state transition before offering recovery.
- The `Run the trust sequence` control creates unique Alpha/Beta names so demonstrations are repeatable without overwriting prior evidence.
- The graph buttons are presentation controls only: they select and explain a node, but they do not change security state. The actual state changes still go through the API controls and are hash-linked in the audit evidence.
- The responsive layout changes the rail into top navigation below 720px, stacks the content grids, enlarges small labels, and turns the three identity actions into full-width touch controls below 460px.
- The readability layer applies a deliberate minimum scale to operational text instead of relying on browser zoom. On narrow phones, audit evidence changes from a six-column table to a two-line card: sequence on the left, event and result on the first line, actor and time on the second line. This preserves the same data while making the story scannable by eye.
- The graph keeps its edge layer in SVG but keeps node copy in normal responsive HTML buttons. That separation matters: the lines can scale with the topology while labels stay at readable CSS pixel sizes. At phone widths, node titles wrap instead of becoming ellipses, and edge labels move between nodes rather than underneath them.

## Problems and limits

The first Compose proxy was aimed at the wrong network namespace; this was found by calling `/api/health` through the browser server, not by looking at source alone. A stale Vite module graph also made the first post-edit browser screenshot look unchanged; restarting only `meridian-web` made the new source visible. The live browser check then observed the button in its `ISSUING X.509 CREDENTIALS…` state and the completed Alpha/Beta result. The current CSS has explicit mobile breakpoints, but a future improvement would add automated screenshot regression at named device sizes.

The current dashboard has no login, role-based UI, websocket stream, pagination, export report, or direct target-service response panel. Token removal is intentionally not a browser button: it is a destructive infrastructure mutation and remains in `run_hsm.ps1`. Those omissions are visible POC limits. The security decisions remain in the API and are audited there. A remaining quality-investment would be automated screenshot regression at named device sizes; the present pass was checked visually at the live narrow browser viewport and through the production build.
