import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActionRequest,
  AuditEvent,
  Certificate,
  Identity,
  Snapshot,
  approveAction,
  createIdentity,
  issueCertificate,
  loadSnapshot,
  openCompromise,
  quarantineIdentity,
  recoverIncident,
  requestAction,
} from "./api";

const emptySnapshot: Snapshot = {
  health: null,
  identities: [],
  certificates: [],
  actions: [],
  incidents: [],
  events: [],
  integrity: null,
  protectedBoundary: null,
};

function formatAge(value: string): string {
  const timestamp = new Date(value).getTime();
  if (Number.isNaN(timestamp)) return "unknown";
  const seconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

function formatDate(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "unknown";
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(date);
}

function shortId(value: string): string {
  return value.length > 18 ? `${value.slice(0, 8)}…${value.slice(-6)}` : value;
}

function tone(value: string): string {
  if (["healthy", "active", "allow", "approved", "success", "resolved", "protected", "verified"].includes(value)) return "good";
  if (["pending", "approval_required", "expiring_soon", "recovery_in_progress"].includes(value)) return "warn";
  if (["deny", "failure", "revoked", "quarantined", "expired", "unavailable", "open", "integrity_failed"].includes(value)) return "bad";
  return "quiet";
}

function StatusPill({ value }: { value: string }) {
  return <span className={`status-pill ${tone(value)}`}><i />{value.replaceAll("_", " ")}</span>;
}

function SectionEyebrow({ number, label }: { number: string; label: string }) {
  return <div className="section-eyebrow"><span>{number}</span><span>{label}</span></div>;
}

type DemoPhase = "idle" | "registering" | "issuing" | "evaluating" | "approval";

const demoPhaseCopy: Record<Exclude<DemoPhase, "idle">, { button: string; title: string; detail: string }> = {
  registering: { button: "Registering Alpha + Beta…", title: "Registering two identities", detail: "Creating one permitted actor and one least-privilege counterexample." },
  issuing: { button: "Issuing X.509 credentials…", title: "Issuing short-lived credentials", detail: "Sending certificate requests through the protected CA boundary." },
  evaluating: { button: "Evaluating policy…", title: "Evaluating intent against authority", detail: "One action should pass, one should fail, and one should pause." },
  approval: { button: "Opening approval gate…", title: "Waiting for a human decision", detail: "The high-risk rotation is paused until an operator approves it." },
};

function splitFingerprint(value: string): string {
  return value.match(/.{1,8}/g)?.join(" · ") ?? value;
}

function App() {
  const [snapshot, setSnapshot] = useState<Snapshot>(emptySnapshot);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ kind: "good" | "bad"; text: string } | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [demoPhase, setDemoPhase] = useState<DemoPhase>("idle");
  const [showAllEvents, setShowAllEvents] = useState(false);
  const refreshInFlight = useRef<Promise<void> | null>(null);

  const refresh = useCallback(async () => {
    if (refreshInFlight.current) {
      await refreshInFlight.current;
      return;
    }
    const request = (async () => {
      try {
        const next = await loadSnapshot();
        setSnapshot(next);
        setConnectionError(null);
        setSelectedId((current) =>
          next.identities.some((identity) => identity.id === current)
            ? current
            : [...next.identities].reverse().find((identity) => identity.name.includes("agent-alpha"))?.id
              ?? next.identities[next.identities.length - 1]?.id
              ?? null,
        );
      } catch (error) {
        setConnectionError(error instanceof Error ? error.message : "API unavailable");
      }
    })();
    refreshInFlight.current = request;
    try {
      await request;
    } finally {
      if (refreshInFlight.current === request) refreshInFlight.current = null;
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 5000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const selectedIdentity = snapshot.identities.find((identity) => identity.id === selectedId) ?? null;
  const selectedCertificates = useMemo(
    () => snapshot.certificates.filter((certificate) => certificate.identity_id === selectedIdentity?.id),
    [snapshot.certificates, selectedIdentity?.id],
  );
  const selectedActiveCertificate = selectedCertificates.find((certificate) => certificate.status === "active") ?? null;
  const recentIdentities = [...snapshot.identities].reverse().slice(0, 12);
  const displayedIdentities = selectedIdentity && !recentIdentities.some((identity) => identity.id === selectedIdentity.id)
    ? [selectedIdentity, ...recentIdentities.slice(0, 11)]
    : recentIdentities;
  const pendingActions = snapshot.actions.filter((action) => action.decision === "approval_required");
  const openIncidents = snapshot.incidents.filter((incident) => incident.status === "open");
  const expiringCertificates = snapshot.certificates.filter((certificate) => ["expiring_soon", "expired"].includes(certificate.lifecycle_status));
  const activeIdentities = snapshot.identities.filter((identity) => identity.status === "active").length;
  const recoveryCompleted = snapshot.events.some((event) => event.event_type === "recovery_completed");
  const hasRecordedDecision = snapshot.events.some((event) => ["action_allowed", "action_denied", "action_approval_required", "action_approved"].includes(event.event_type));
  const hasCertificateEvidence = snapshot.events.some((event) => event.event_type === "certificate_issued");
  const hasContainmentEvidence = snapshot.events.some((event) => ["identity_quarantined", "certificate_revoked"].includes(event.event_type));
  const storyStep = openIncidents.length > 0 ? 3 : recoveryCompleted ? 4 : hasRecordedDecision ? 2 : snapshot.identities.length > 0 ? 1 : 1;
  const displayedEvents = showAllEvents ? [...snapshot.events].reverse() : [...snapshot.events].reverse().slice(0, 8);
  const liveSequence = [
    { label: "IDENTITIES", detail: `${snapshot.identities.length} registered`, reached: snapshot.identities.length > 0 },
    { label: "X.509 / PKI", detail: `${snapshot.certificates.length} issued`, reached: hasCertificateEvidence || snapshot.certificates.length > 0 },
    { label: "POLICY", detail: `${snapshot.actions.length} decisions`, reached: hasRecordedDecision },
    { label: "CONTAINMENT", detail: openIncidents.length > 0 ? "isolate the unknown" : recoveryCompleted || hasContainmentEvidence ? "evidence recorded" : "standby", reached: openIncidents.length > 0 || recoveryCompleted || hasContainmentEvidence },
  ];
  const recentIncidents = [...snapshot.incidents].reverse();
  const displayedIncidents = [...openIncidents, ...recentIncidents.filter((incident) => incident.status !== "open").slice(0, Math.max(0, 4 - openIncidents.length))];
  const liveState = demoPhase !== "idle"
    ? demoPhaseCopy[demoPhase]
    : openIncidents.length > 0
      ? { title: "Containment is active", detail: "An unknown credential is isolated while the audit chain records the response." }
      : pendingActions.length > 0
        ? { title: "Human approval is the next gate", detail: "A high-risk action is paused; the operator decision is visible in the policy panel." }
        : hasRecordedDecision
          ? { title: "Policy has a recorded decision", detail: "Allowed and denied actions are visible beside their certificates and evidence." }
          : snapshot.health?.status === "healthy"
            ? { title: "Ready to prove trust", detail: "Launch the sequence to create identities, issue credentials, and exercise policy." }
            : { title: "Connecting to the trust surface", detail: "The console is waiting for the API and protected CA to report healthy." };
  const liveCurrentIndex = demoPhase === "registering" ? 0 : demoPhase === "issuing" ? 1 : demoPhase === "evaluating" || demoPhase === "approval" ? 2 : openIncidents.length > 0 ? 3 : recoveryCompleted ? 3 : hasRecordedDecision ? 2 : hasCertificateEvidence ? 1 : 0;

  async function perform(label: string, operation: () => Promise<unknown>, success: string) {
    setBusy(label);
    setNotice(null);
    try {
      await operation();
      await refresh();
      setNotice({ kind: "good", text: success });
    } catch (error) {
      setNotice({ kind: "bad", text: error instanceof Error ? error.message : "Operation failed" });
    } finally {
      setBusy(null);
    }
  }

  async function launchStory() {
    setBusy("story");
    setDemoPhase("registering");
    setNotice(null);
    const run = crypto.randomUUID().slice(0, 8);
    try {
      const alpha = await createIdentity({
        name: `agent-alpha-${run}`,
        kind: "agent",
        owner: "meridian-console",
        purpose: "primary actor in the trust-under-pressure story",
        allowed_actions: ["read_status", "rotate_certificate"],
      });
      const beta = await createIdentity({
        name: `agent-beta-${run}`,
        kind: "agent",
        owner: "meridian-console",
        purpose: "least-privilege counterexample",
        allowed_actions: ["read_status"],
      });
      setDemoPhase("issuing");
      const alphaCertificate = await issueCertificate(alpha.id, alpha.name);
      const betaCertificate = await issueCertificate(beta.id, beta.name);
      setDemoPhase("evaluating");
      await requestAction(alpha.id, {
        action: "read_status",
        target: "service-a",
        certificate_fingerprint: alphaCertificate.fingerprint,
      });
      await requestAction(beta.id, {
        action: "delete_data",
        target: "service-a",
        certificate_fingerprint: betaCertificate.fingerprint,
      });
      setDemoPhase("approval");
      await requestAction(alpha.id, {
        action: "rotate_certificate",
        target: alpha.name,
        certificate_fingerprint: alphaCertificate.fingerprint,
      });
      setSelectedId(alpha.id);
      await refresh();
      setNotice({ kind: "good", text: "Story launched: Alpha is awaiting approval; Beta was denied." });
    } catch (error) {
      setNotice({ kind: "bad", text: error instanceof Error ? error.message : "Could not launch the story" });
    } finally {
      setDemoPhase("idle");
      setBusy(null);
    }
  }

  function identityAction(identity: Identity) {
    const certificate = snapshot.certificates.find(
      (item) => item.identity_id === identity.id && item.status === "active",
    );
    if (!certificate) return null;
    return certificate;
  }

  return (
    <main className="app-shell min-h-screen overflow-x-hidden bg-slate-950/0 text-slate-100">
      <aside className="side-rail shadow-panel">
        <div className="brand-mark"><span className="brand-orbit" /><span className="brand-word">MERIDIAN</span><span className="brand-sub">TRUST OPERATIONS</span></div>
        <div className="rail-rule" />
        <nav aria-label="Primary navigation">
          <a className="nav-link active" href="#overview"><span className="nav-icon">◈</span>Overview<span className="nav-index">01</span></a>
          <a className="nav-link" href="#identities"><span className="nav-icon">◎</span>Identities<span className="nav-index">02</span></a>
          <a className="nav-link" href="#boundary"><span className="nav-icon">⌘</span>Boundary<span className="nav-index">03</span></a>
          <a className="nav-link" href="#incidents"><span className="nav-icon">△</span>Incidents<span className="nav-index">04</span></a>
          <a className="nav-link" href="#evidence"><span className="nav-icon">≋</span>Evidence<span className="nav-index">05</span></a>
        </nav>
        <div className="rail-bottom">
          <div className="rail-caption">LOCAL LAB / SYNTHETIC DATA</div>
          <div className="rail-system"><span className="pulse-dot" />All systems observable</div>
          <div className="rail-version">MERIDIAN POC <span>v0.1</span></div>
        </div>
      </aside>

      <section className="content-shell">
        <header className="topbar sticky top-0 z-20 bg-slate-950/60 backdrop-blur-xl">
          <div className="breadcrumb"><span>CONTROL ROOM</span><b>/</b><span className="muted">TRUST OPERATIONS</span></div>
          <div className="top-actions">
            <span className="last-refresh">LIVE POLL / 5 SEC</span>
            <span className={`health-indicator ${snapshot.health?.status === "healthy" ? "online" : "offline"}`}><i />{snapshot.health?.status ?? "connecting"}</span>
          </div>
        </header>

        <div className="page-content" id="overview">
          <section className="hero-grid">
            <div className="hero-copy">
              <SectionEyebrow number="00" label="THE TRUST SURFACE" />
              <h1>Make trust legible.<br /><em>Keep it in motion.</em></h1>
              <p className="hero-lede">Meridian turns machine and agent identity into an observable operating story—from first issuance to the moment a compromised credential is contained.</p>
              <div className="hero-cta-row">
                <button className="primary-button rounded-sm shadow-aura focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-meridian-cyan/70" onClick={() => void launchStory()} disabled={busy !== null}>
                  <span className="button-glyph">{busy === "story" ? "◌" : "+"}</span>{busy === "story" && demoPhase !== "idle" ? demoPhaseCopy[demoPhase].button : "Run the trust sequence"}<span className="button-arrow">↗</span>
                </button>
                <a className="text-link underline-offset-4 hover:underline" href="#evidence">Trace the evidence <span>↓</span></a>
              </div>
              {(notice || connectionError) && <div className={`notice ${notice?.kind ?? "bad"}`} role="status">{notice?.text ?? `API: ${connectionError}`}</div>}
              <div className="live-protocol" aria-live="polite">
                <div className="live-protocol-top"><span className="live-label"><i /> LIVE EXECUTION</span><span className="live-poll-label">API SNAPSHOT / 5 SEC</span></div>
                <div className="live-protocol-main"><div><strong>{liveState.title}</strong><p>{liveState.detail}</p></div><div className="live-event-count"><b>{snapshot.events.length.toString().padStart(3, "0")}</b><span>events<br />linked</span></div></div>
                <div className="protocol-steps">
                  {liveSequence.map((step, index) => <div className={`protocol-step ${step.reached ? "reached" : ""} ${index === liveCurrentIndex ? "current" : ""}`} key={step.label}><span className="protocol-dot">{step.reached ? "✓" : `0${index + 1}`}</span><div><strong>{step.label}</strong><small>{demoPhase !== "idle" && index === liveCurrentIndex ? demoPhaseCopy[demoPhase].detail : step.detail}</small></div></div>)}
                </div>
              </div>
            </div>
            <div className="constellation-card rounded-xl shadow-panel" aria-label="Live trust constellation">
              <div className="card-topline"><span>OBSERVED TRUST TOPOLOGY</span><span className="coordinates">MERIDIAN / 01</span></div>
              <div className="constellation-stage">
                <div className="orbit orbit-a" /><div className="orbit orbit-b" /><div className="orbit orbit-c" />
                <div className="constellation-line line-one" /><div className="constellation-line line-two" /><div className="constellation-line line-three" />
                <div className="constellation-node ca-node"><span className="node-core">✦</span><strong>ISSUING CA</strong><small>{snapshot.health?.certificate_authority ?? "checking"}</small></div>
                <div className="constellation-node api-node"><span className="node-core">⌁</span><strong>CONTROL API</strong><small>{snapshot.health?.database ?? "checking"}</small></div>
                <div className="constellation-node agent-node"><span className="node-core">◌</span><strong>AGENTS</strong><small>{snapshot.identities.filter((item) => item.kind === "agent").length} observed</small></div>
                <div className="constellation-node service-node"><span className="node-core">⊙</span><strong>SERVICES</strong><small>mTLS mesh</small></div>
                <div className="constellation-center"><span>MERIDIAN</span><b>TRUST<br />GRAPH</b></div>
              </div>
              <div className="constellation-legend"><span><i className="legend-good" />healthy</span><span><i className="legend-line" />audited link</span><span><i className="legend-orbit" />protected boundary</span></div>
            </div>
          </section>

          <section className="metrics-grid" aria-label="Trust metrics">
            <div className="metric-card metric-feature rounded-xl shadow-panel"><div className="metric-label">ACTIVE IDENTITIES <span>01</span></div><strong>{activeIdentities.toString().padStart(2, "0")}</strong><div className="metric-foot"><span className="trend-up">↗</span> registered in trust domain</div><div className="metric-spark"><i /><i /><i /><i /><i /><i /><i /></div></div>
            <div className="metric-card rounded-xl shadow-panel"><div className="metric-label">EXPIRY RADAR <span>02</span></div><strong>{expiringCertificates.length.toString().padStart(2, "0")}</strong><div className="metric-foot"><span className={expiringCertificates.length ? "trend-warn" : "trend-up"}>{expiringCertificates.length ? "!" : "✓"}</span>{expiringCertificates.length ? " attention required" : " within safe horizon"}</div></div>
            <div className="metric-card rounded-xl shadow-panel"><div className="metric-label">OPEN INCIDENTS <span>03</span></div><strong>{openIncidents.length.toString().padStart(2, "0")}</strong><div className="metric-foot"><span className={openIncidents.length ? "trend-warn" : "trend-up"}>{openIncidents.length ? "↯" : "✓"}</span>{openIncidents.length ? " containment active" : " no active threats"}</div></div>
            <div className="metric-card rounded-xl shadow-panel"><div className="metric-label">AUDIT SEQUENCE <span>04</span></div><strong>{snapshot.events.length.toString().padStart(2, "0")}</strong><div className="metric-foot"><span className="trend-up">⌁</span> hash-linked events</div></div>
          </section>

          <section className="story-section">
            <div className="story-header"><div><SectionEyebrow number="01" label="THE NARRATIVE" /><h2>Every credential has a story.</h2></div><span className="story-context">A guided view of the trust lifecycle</span></div>
            <div className="story-track">
              {["Observe", "Decide", "Contain", "Recover"].map((label, index) => <div className={`story-beat ${index + 1 <= storyStep ? "reached" : ""} ${index + 1 === storyStep ? "current" : ""}`} key={label}><div className="beat-index">0{index + 1}</div><div className="beat-line"><span /></div><strong>{label}</strong><small>{["see the trust graph", "policy meets intent", "isolate the unknown", "restore with proof"][index]}</small></div>)}
            </div>
          </section>

          <section className="boundary-section" id="boundary">
            <div className="panel boundary-panel rounded-xl shadow-panel">
              <div className="panel-heading">
                <div><SectionEyebrow number="02" label="PROTECTED KEY BOUNDARY" /><h2>Signing stays behind the line.</h2></div>
                <StatusPill value={snapshot.protectedBoundary?.status === "healthy" ? "protected" : snapshot.protectedBoundary ? "unavailable" : "checking"} />
              </div>
              <div className="boundary-grid">
                <div className="boundary-visual" aria-label="PKCS11 protected key boundary">
                  <div className="boundary-ring boundary-ring-one" /><div className="boundary-ring boundary-ring-two" />
                  <div className="boundary-lock">▣</div><strong>PKCS#11</strong><small>signing boundary</small><span className="boundary-visual-status"><i /> private key isolated</span>
                </div>
                <div className="boundary-facts">
                  <div><span>TOKEN</span><strong>{snapshot.protectedBoundary?.token_label ?? "checking"}</strong></div>
                  <div><span>KEY STORE</span><strong>{snapshot.protectedBoundary?.key_store ?? "checking"}</strong></div>
                  <div><span>CA LINK</span><strong>{snapshot.protectedBoundary?.status === "healthy" ? "reachable · verified" : snapshot.protectedBoundary?.status ?? "checking"}</strong></div>
                  <div><span>API DISK ACCESS</span><strong>{snapshot.protectedBoundary?.api_disk_key_access ?? "checking"}</strong></div>
                </div>
                <div className="boundary-copy">
                  <p>The API can request a certificate, but it never receives the CA signing key. The live panel checks the separate HSM-backed CA; the token-loss exercise remains an explicit terminal workflow because the browser should observe that boundary, not control it.</p>
                  <div className="boundary-objects"><span>OBJECTS</span>{(snapshot.protectedBoundary?.key_objects ?? ["waiting for token"]).map((object) => <code key={object}>{object}</code>)}</div>
                  <div className="boundary-callout"><span>REQUEST PATH</span><strong>API request <b>→</b> HSM sign <b>→</b> certificate returned</strong></div>
                </div>
              </div>
            </div>
          </section>

          <section className="workspace-grid" id="identities">
            <div className="panel identities-panel rounded-xl shadow-panel">
              <div className="panel-heading"><div><SectionEyebrow number="03" label="IDENTITY REGISTRY" /><h2>Who is trusted?</h2></div><span className="panel-count">{displayedIdentities.length.toString().padStart(2, "0")} latest / {snapshot.identities.length} total</span></div>
              <div className="identity-list">
                {snapshot.identities.length === 0 && <div className="empty-state">No identities yet. Run the trust sequence to create the first synthetic agent.</div>}
                {displayedIdentities.map((identity) => {
                  const certificate = identityAction(identity);
                  return <button className={`identity-row focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-meridian-cyan ${identity.id === selectedId ? "selected" : ""}`} key={identity.id} onClick={() => setSelectedId(identity.id)}>
                    <span className={`identity-avatar ${identity.kind}`}><span>{identity.kind === "agent" ? "◌" : "⊙"}</span></span>
                    <span className="identity-main"><strong>{identity.name}</strong><small>{identity.kind} / owned by {identity.owner}</small></span>
                    <span className="identity-purpose">{identity.purpose}</span>
                    <span className="identity-certificate">{certificate ? <><i className="cert-seal">◇</i><span><b>{certificate.lifecycle_status}</b><small>{shortId(certificate.fingerprint)}</small></span></> : <span className="no-cert">NO CREDENTIAL</span>}</span>
                    <StatusPill value={identity.status} /><span className="row-chevron">→</span>
                  </button>;
                })}
              </div>
            </div>

            <div className="panel identity-detail-panel rounded-xl shadow-panel">
              <div className="panel-heading compact"><div><SectionEyebrow number="04" label="SELECTED IDENTITY" /><h2>{selectedIdentity?.name ?? "Awaiting identity"}</h2></div><span className="detail-orb">✦</span></div>
              {selectedIdentity ? <>
                <div className="detail-meta"><div><span>OWNER</span><strong>{selectedIdentity.owner}</strong></div><div><span>PURPOSE</span><strong>{selectedIdentity.purpose}</strong></div></div>
                <div className="authority-block"><div className="authority-title"><span>AUTHORITY ENVELOPE</span><em>{selectedIdentity.allowed_actions.length} grants</em></div><div className="tag-cloud">{selectedIdentity.allowed_actions.map((action) => <span key={action}>{action}</span>)}</div></div>
                <div className="certificate-dossier">
                  <div className="dossier-top"><div className="dossier-seal">✦</div><div><span>X.509 / SHORT-LIVED</span><strong>{selectedActiveCertificate ? "ACTIVE CREDENTIAL" : "CREDENTIAL SLOT"}</strong></div>{selectedActiveCertificate && <StatusPill value={selectedActiveCertificate.lifecycle_status} />}</div>
                  {selectedActiveCertificate ? <><div className="dossier-grid"><div><span>ISSUER</span><strong>{selectedActiveCertificate.issuer}</strong></div><div><span>ALGORITHM</span><strong>{selectedActiveCertificate.key_algorithm}</strong></div><div><span>SERIAL</span><strong>{shortId(selectedActiveCertificate.serial_number)}</strong></div><div><span>EXPIRES</span><strong>{formatDate(selectedActiveCertificate.not_after)}</strong></div></div><div className="dossier-fingerprint"><span>SHA-256 FINGERPRINT</span><code>{splitFingerprint(selectedActiveCertificate.fingerprint)}</code></div></> : <div className="cert-missing">No active certificate. Issue one to unlock policy actions.</div>}
                </div>
                <div className="detail-actions"><button className="secondary-button rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-meridian-cyan/70" disabled={busy !== null} onClick={() => void perform("issue", () => issueCertificate(selectedIdentity.id, selectedIdentity.name), "Short-lived certificate issued.")}>{busy === "issue" ? "Issuing…" : "Issue certificate"}</button><button className="ghost-button rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-meridian-cyan/70" disabled={busy !== null || selectedIdentity.status !== "active"} onClick={() => void perform("quarantine", () => quarantineIdentity(selectedIdentity.id), "Identity quarantined.")}>Quarantine</button><button className="ghost-button danger rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-meridian-red/70" disabled={busy !== null || selectedIdentity.status === "revoked"} onClick={() => void perform("compromise", () => openCompromise(selectedIdentity.id, "operator-triggered synthetic compromise"), "Compromise contained; incident opened.")}>Simulate compromise</button></div>
              </> : <div className="detail-empty">Select an identity from the registry.</div>}
            </div>
          </section>

          <section className="lower-grid" id="incidents">
             <div className="panel incidents-panel"><div className="panel-heading"><div><SectionEyebrow number="05" label="ISOLATE THE UNKNOWN" /><h2>When trust breaks.</h2></div><span className="panel-count">{snapshot.incidents.length.toString().padStart(2, "0")} stories</span></div><div className="incident-list">{snapshot.incidents.length === 0 && <div className="empty-state">No incidents. The quiet is earned by observable controls.</div>}{displayedIncidents.map((incident) => { const owner = snapshot.identities.find((identity) => identity.id === incident.identity_id); const stages = incident.status === "open" ? ["presented", "unknown", "quarantined", "revoked"] : ["detected", "quarantined", "revoked", "recovered"]; const activeStage = incident.status === "open" ? 2 : 3; return <div className={`incident-card ${incident.status}`} key={incident.id}><div className="incident-spine"><span>{incident.status === "open" ? "↯" : "✓"}</span></div><div className="incident-content"><div className="incident-top"><strong>{incident.reason}</strong><StatusPill value={incident.status} /></div><p>{owner?.name ?? shortId(incident.identity_id)} <span>·</span> opened {formatAge(incident.created_at)}</p><div className="isolation-badge"><i />{incident.status === "open" ? "UNKNOWN CREDENTIAL ISOLATED" : "IDENTITY RESTORED WITH PROOF"}</div><div className="containment-track">{stages.map((stage, index) => <span className={index <= activeStage ? "done" : ""} key={stage}><i />{stage}</span>)}</div>{incident.status === "open" ? <button className="inline-action" disabled={busy !== null} onClick={() => void perform("recover", () => recoverIncident(incident.id), "Replacement credential issued; identity recovered.")}>Begin verified recovery <span>↗</span></button> : <div className="resolved-copy">Recovered {formatDate(incident.resolved_at)} <span>· evidence complete</span></div>}</div></div>; })}</div></div>

            <div className="panel decision-panel"><div className="panel-heading"><div><SectionEyebrow number="06" label="POLICY GATE" /><h2>Intent meets authority.</h2></div><span className="panel-count">{pendingActions.length.toString().padStart(2, "0")} pending</span></div><div className="decision-list">{pendingActions.length === 0 && <div className="empty-state">No actions waiting for a human. Run the trust sequence to open an approval gate.</div>}{pendingActions.slice(-4).reverse().map((action: ActionRequest) => { const identity = snapshot.identities.find((item) => item.id === action.identity_id); return <div className="decision-card" key={action.id}><div className="decision-mark">!</div><div className="decision-content"><div className="decision-top"><strong>{action.action}</strong><span className="risk-label">{action.risk_level} risk</span></div><p>{identity?.name ?? shortId(action.identity_id)} <span>→</span> {action.target}</p><small>{action.reason}</small><button className="approve-button" disabled={busy !== null} onClick={() => void perform("approve", () => approveAction(action.id), "Operator approval recorded; action completed.")}>Approve action <span>↗</span></button></div></div>; })}</div></div>
          </section>

          <section className="evidence-section" id="evidence"><div className="panel evidence-panel"><div className="panel-heading"><div><SectionEyebrow number="07" label="AUDIT EVIDENCE" /><h2>The system remembers.</h2></div><div className="integrity-meta"><StatusPill value={snapshot.integrity ? snapshot.integrity.valid ? "verified" : "integrity_failed" : "checking"} /><span>{snapshot.integrity ? `${snapshot.integrity.checked_through_sequence}/${snapshot.integrity.event_count} checked` : "waiting for evidence"}</span><button className="text-button" onClick={() => setShowAllEvents((value) => !value)}>{showAllEvents ? "Show recent" : "View full sequence"} ↗</button></div></div><div className="audit-table"><div className="audit-table-head"><span>SEQ</span><span>EVENT</span><span>ACTOR / SUBJECT</span><span>RESULT</span><span>WHEN</span><span>CHAIN</span></div>{displayedEvents.length === 0 && <div className="empty-state">Audit evidence will appear here after the first state change.</div>}{displayedEvents.map((event: AuditEvent) => <div className="audit-row" key={event.id}><span className="audit-seq">{event.sequence.toString().padStart(3, "0")}</span><span className="audit-event"><i className={`event-dot ${tone(event.result)}`} /><strong>{event.event_type.replaceAll("_", " ")}</strong></span><span className="audit-actor">{event.actor}<small>{shortId(event.subject)}</small></span><StatusPill value={event.result} /><span className="audit-time">{formatAge(event.timestamp)}</span><span className="chain-link">{event.previous_event_hash ? "linked ↗" : "genesis ◇"}</span></div>)}</div>{snapshot.integrity && !snapshot.integrity.valid && <div className="integrity-warning" role="alert">Integrity check stopped at sequence {snapshot.integrity.first_invalid_sequence ?? "unknown"}: {snapshot.integrity.error ?? "audit chain is not valid"}.</div>}</div></section>

          <footer className="footer"><span>PROJECT MERIDIAN / DIGITAL TRUST OPERATIONS</span><span>LOCAL POC · SYNTHETIC DATA · NOT PRODUCTION</span><span>BUILDING TRUST, ONE EVENT AT A TIME ✦</span></footer>
        </div>
      </section>
    </main>
  );
}

export default App;
