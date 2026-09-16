# React dashboard milestone

## Purpose

The dashboard makes Meridian's invisible security activity understandable without inventing a second source of truth. It reads the API's health, identity, certificate, action, incident, audit, and protected-boundary endpoints and turns them into one operational narrative.

## Visual language

The interface is a dark, instrument-like control room rather than a generic CRUD table:

- a live trust topology uses restrained CSS perspective, orbit rings, network lines, and protected-boundary nodes;
- React/Tailwind provides the component and utility system; bespoke CSS is limited to the authored 3D scene, typography tokens, editorial grid, and motion rules;
- the hero copy frames trust as a lifecycle story;
- four story beats show observe, decide, contain, and recover;
- registry rows make ownership, purpose, credential state, and authority visible;
- the policy gate surfaces human approval as a deliberate pause;
- the incident theatre shows open versus resolved response state;
- the audit table exposes sequence numbers, event result, time, and hash-chain linkage.
- the evidence header verifies the complete hash chain and reports the first broken sequence if stored evidence is tampered with.
- the protected-key panel checks the separate HSM-backed CA and shows the PKCS#11 token/object boundary without exposing key material.

The 3D effect is CSS-only and decorative. It does not alter security decisions. The browser never receives a CA private key or a private-key path.

## Real interactions

- `Run the trust sequence` creates synthetic Agent Alpha and Agent Beta, issues both certificates, records Alpha's allowed action, records Beta's denied `delete_data` request, and opens Alpha's high-risk approval request.
- Identity detail actions issue a certificate, quarantine an identity, or open the compromise flow.
- Pending high-risk actions can be approved from the policy gate.
- Open incidents can be recovered from the incident theatre.
- The protected-boundary panel reports live `hsm-ca` reachability, the `meridian-hsm` token identity, PKCS#11 objects, and the fact that CA private-key files are not mounted into the API.
- The page polls the API every five seconds and exposes failures instead of replacing them with fake green state.
- Polls are serialized so a slow request cannot be overtaken by a newer request and overwrite the screen with stale data. Selection is also repaired if the selected identity disappears.

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

## Problems found and fixed

1. The first container proxy check returned `ECONNREFUSED` because the Vite target was `localhost:8000` from inside the web container. A Compose-specific `VITE_API_TARGET` now points to `meridian-api`, while host development keeps the localhost default.
2. The first host type-check failed because Vite's `process.env` access lacked Node declarations. `@types/node` was added and the production build passed.
3. Browser visual automation could not start because the local CUA helper reported a missing kernel-assets path. Functional HTML, proxy, build, and service checks still passed; a manual visual browser review remains a limitation of this environment, not a claim that screenshots were inspected.
