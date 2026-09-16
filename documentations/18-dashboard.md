# React dashboard milestone

## Purpose

The dashboard makes Meridian's invisible security activity understandable without inventing a second source of truth. It reads the API's health, identity, certificate, action, incident, audit, and protected-boundary endpoints and turns them into one operational narrative.

## Visual language

The interface is a dark, instrument-like control room rather than a generic CRUD table:

- a live trust graph renders real directed SVG edges between the protected HSM, issuing CA, Meridian control plane, API, agents, and mTLS services; selecting a node highlights its connected edges and updates the explanation below;
- React/Tailwind provides the component and utility system; bespoke CSS is limited to the authored 3D scene, typography tokens, editorial grid, and motion rules;
- the hero copy frames trust as a lifecycle story;
- four story beats show observe, decide, contain, and recover;
- registry rows make ownership, purpose, credential state, and authority visible;
- the policy gate surfaces human approval as a deliberate pause;
- the incident theatre shows open versus resolved response state;
- the audit table exposes sequence numbers, event result, time, and hash-chain linkage.
- the evidence header verifies the complete hash chain and reports the first broken sequence if stored evidence is tampered with.
- the protected-key panel checks the separate HSM-backed CA and shows the PKCS#11 token/object boundary without exposing key material.
- graph labels and health values come from the live snapshot; the graph is a topology view, not a substitute cryptographic proof graph.
- the live execution panel narrates the API snapshot with four evidence checkpoints: identities, X.509/PKI, policy, and containment.
- the operator trace turns those checkpoints into four server-facing checks with `queued`, `checking`, and `verified` states, endpoint labels, and the latest audit event; the running state adds a small scan cue so activity is visible without pretending to be a network animation.
- the final contrast pass gives both themes stronger secondary text, heavier operational labels, clearer audit/graph copy, and visible keyboard focus without changing the meaning of any status color.
- the selected-identity panel presents an X.509 dossier with issuer, algorithm, serial, expiry, and a SHA-256 fingerprint; it never displays private key material.
- incident cards make `presented -> unknown -> quarantined -> revoked` and `detected -> quarantined -> revoked -> recovered` visible as state tracks.
- the red `OPEN ↗` control is now an actual incident-details button: it expands the response explanation in place, while `Begin verified recovery ↗` remains the state-changing API action.

The graph is an observable topology view and does not alter security decisions. The browser never receives a CA private key or a private-key path.

## Real interactions

- `Run the trust sequence` creates synthetic Agent Alpha and Agent Beta, issues both certificates, records Alpha's allowed action, records Beta's denied `delete_data` request, and opens Alpha's high-risk approval request.
- During that sequence the button changes to `Registering Alpha + Beta`, `Issuing X.509 credentials`, `Evaluating policy`, and `Opening approval gate`, so the operator can see which real request is in progress.
- The sequence deliberately pauses between registration, issuance, the allowed/denied policy checks, and the approval gate. Each checkpoint refreshes the API snapshot, so counters, graph health, and audit evidence visibly catch up while the operator is watching.
- The top-bar theme control switches between the graphite dark console and a readable light console. The choice is stored in `localStorage`, the same live values and status colors remain in both modes, and the control is available as an accessible toggle.
- Identity detail actions issue a certificate, quarantine an identity, or open the compromise flow.
- Pending high-risk actions can be approved from the policy gate.
- Open incidents can be recovered from the incident theatre.
- Recovery now exposes `Recovering incident…` during the request and then visibly changes the card to `RESOLVED`, increments the certificate/audit counts, and shows the success notice.
- The protected-boundary panel reports live `hsm-ca` reachability, the `meridian-hsm` token identity, PKCS#11 objects, and the fact that CA private-key files are not mounted into the API.
- The page polls the API every five seconds and exposes failures instead of replacing them with fake green state.
- Polls are serialized so a slow request cannot be overtaken by a newer request and overwrite the screen with stale data. Selection is also repaired if the selected identity disappears.
- The registry opens on the newest twelve identities while preserving the full total in the API and audit history. When a demo Alpha exists, the latest Alpha is selected so the approval story is the first credential dossier shown. This keeps repeated synthetic runs from pushing the incident and evidence panels out of reach.
- At widths below 720px the fixed rail becomes a horizontally scrollable top navigation, grids stack, buttons become comfortable touch targets, metadata grows, and low-priority columns collapse. Below 460px the detail actions stack and the HSM facts become one column. The final readability pass raises operational labels, metadata, status pills, graph labels, and evidence text; on phone widths the audit table becomes two-line evidence cards so event, actor, result, and time remain readable without desktop-sized columns.
- Navigation is scroll-aware: the active tab is initialized from the URL hash, changes immediately on click, follows the section crossing a viewport-aware reading marker, exposes `aria-current`, and keeps the selected tab in view when the compact mobile nav overflows horizontally. The desktop rail also explains the active step as `see the trust graph`, `name who is trusted`, `prove keys stay protected`, `contain the unknown`, or `verify what happened`.
- The page keeps vertical scrolling on the document. Horizontal clipping belongs to `body`, not the React `<main>`, because an `overflow-x-hidden` shell can become a competing scroll container and make hash links, `window.scrollY`, and the visible section disagree.

## Local run

Host development uses `npm run dev` in `apps/web` and proxies `/api` to `http://localhost:8000`. Compose sets `VITE_API_TARGET=http://meridian-api:8000` because `localhost` inside the web container means the web container itself.

From the web folder run `npm install` and `npm run build`.

Or start the full local console from the project root with `docker compose up -d meridian-web`. Open `http://127.0.0.1:5173` in a browser. Using the IPv4 loopback avoids Windows/Docker Desktop IPv6 loopback differences.

## Verification performed

- TypeScript project build passed.
- Vite production bundle passed.
- `GET http://127.0.0.1:5173/` returned HTTP 200 and the Meridian title.
- `GET http://127.0.0.1:5173/api/health` returned healthy API, database, and certificate authority states through the Compose proxy.
- `GET http://127.0.0.1:5173/api/protected-boundary` returned the HSM-backed CA status through the Compose proxy.
- The dashboard source is wired to the real API rather than static sample data.
- In-browser verification showed the button entering the disabled `ISSUING X.509 CREDENTIALS…` state, then completing with the notice `Story launched: Alpha is awaiting approval; Beta was denied.` The same run updated the live counters, selected Alpha, rendered the certificate dossier, and added the latest audit events.
- Visual inspection showed the protected panel with `PKCS#11`, `meridian-hsm`, `PKCS#11 / SoftHSM2`, `private key isolated`, and the request path `API request -> HSM sign -> certificate returned`.
- Visual inspection at the narrow in-app-browser viewport showed the enlarged audit entries as readable cards, including event names such as `Certificate Revoked`, actor/fingerprint context, `SUCCESS`, sequence numbers, and relative times.
- Visual inspection at the narrow in-app-browser viewport showed the connected graph with readable `PROTECTED HSM`, `ISSUING CA`, `MERIDIAN`, `CONTROL API`, `AGENTS`, and `SERVICES` nodes plus directed `PKCS#11`, `X.509`, `mTLS`, `policy`, and `evidence` edges. Clicking `AGENTS` changed the selected-node readout and reduced the graph to its two related edges.
- Visual inspection showed the live operator trace moving through `CHECKING` during the showcase and `VERIFIED` after the final refresh, with real API endpoint labels and the latest audit event. The light-mode toggle remained active after a reload and the live data rehydrated without changing the theme.
- Visual inspection after the contrast pass showed the larger, heavier headings, metadata, status labels, graph copy, audit actors, and trace details in both the light and dark themes at the narrow browser viewport.
- The navigation/brand pass showed the light-mode wordmark inheriting the shell's pale Tailwind text color and the rail always marking Overview active. The layered orbit mark now has explicit ink, and the scroll-aware state keeps the selected section honest.
- A browser recheck found that mobile tab alignment was using `scrollIntoView()` on a link inside the top rail. That could pull the document back to the rail after an anchor click. The fix scrolls only the nav element horizontally with `nav.scrollTo()` and leaves the page's section jump intact.
- The wide-screen evidence review showed a second state bug: the evidence panel was visible while the fixed 150px reading line still belonged to Incidents. The scroll marker is now 40% of the viewport, bounded between 180px and 420px, so the selected rail step follows what the reader is actually looking at across desktop and mobile sizes.
- Hover styling is intentionally weaker than active styling. This prevents the pointer resting over an adjacent tab from looking like a second selected section, while `:focus-visible` keeps keyboard navigation obvious.

## Problems found and fixed

1. The first container proxy check returned `ECONNREFUSED` because the Vite target was `localhost:8000` from inside the web container. A Compose-specific `VITE_API_TARGET` now points to `meridian-api`, while host development keeps the localhost default.
2. The first host type-check failed because Vite's `process.env` access lacked Node declarations. `@types/node` was added and the production build passed.
3. One earlier browser tab held a stale Vite module graph after a source edit. Restarting only `meridian-web` refreshed the module graph; the browser then showed the new live panel and the real in-progress sequence. The current visual review used the local in-app browser. The responsive CSS is covered by explicit 720px and 460px breakpoints; an automated pixel-diff across multiple device widths is still future work.
4. The first audit layout was technically responsive but still too small to scan. A final CSS readability layer increased the type scale across the console and replaces the phone audit grid with stacked cards under 520px. This keeps the evidence hierarchy intact while preventing actors, results, and timestamps from collapsing into microscopic cells.
5. The first topology was visually evocative but not a graph: it used orbit decoration and loose connector lines. The graph was replaced with an SVG edge layer plus live, selectable node buttons. This makes relationships inspectable while preserving the editorial visual language.
6. On a narrow viewport, identity grid children retained their intrinsic desktop widths, which pushed status pills into the chevron and clipped labels such as `QUARANTINED`. `min-width: 0`, responsive grid columns, and a dedicated chevron column now keep identity names, state pills, and row links separated and readable.
7. A single “running” label did not make the showcase feel observable enough. The operator trace now pairs each phase with the real API checkpoint it represents, shows what is queued or being checked, and surfaces the last event the server wrote to the hash chain. The theme control uses the same tokenized status system in both light and dark modes.
8. The earlier readability pass increased size but left some secondary text too pale and too light in weight. The final contrast layer raises the muted/faint token contrast, gives operational text a 500–700 weight range, and uses explicit light/dark overrides for audit, graph, dossier, protocol, and status copy.
