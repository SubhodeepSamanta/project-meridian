export type Health = {
  status: string;
  database: string;
  certificate_authority: string;
};

export type Identity = {
  id: string;
  name: string;
  kind: "service" | "agent";
  owner: string;
  purpose: string;
  status: string;
  allowed_actions: string[];
  certificate_fingerprint: string | null;
  created_at: string;
};

export type Certificate = {
  id: string;
  identity_id: string;
  serial_number: string;
  subject: string;
  issuer: string;
  not_before: string;
  not_after: string;
  status: string;
  lifecycle_status: string;
  key_algorithm: string;
  fingerprint: string;
  renewal_status: string;
  created_at: string;
};

export type ActionRequest = {
  id: string;
  identity_id: string;
  action: string;
  target: string;
  risk_level: string;
  approval_status: string;
  decision: string;
  reason: string;
  execution_result: Record<string, unknown>;
  requested_at: string;
};

export type Incident = {
  id: string;
  identity_id: string;
  status: string;
  reason: string;
  created_at: string;
  resolved_at: string | null;
};

export type AuditEvent = {
  id: string;
  event_type: string;
  actor: string;
  subject: string;
  result: string;
  reason: string;
  correlation_id: string;
  incident_id: string | null;
  payload: Record<string, unknown>;
  previous_event_hash: string | null;
  event_hash: string;
  sequence: number;
  timestamp: string;
};

export type AuditIntegrity = {
  valid: boolean;
  event_count: number;
  checked_through_sequence: number;
  first_invalid_sequence: number | null;
  error: string | null;
};

export type ProtectedBoundary = {
  status: string;
  token_label: string;
  key_store: string;
  key_objects: string[];
  api_disk_key_access: string;
  ca_endpoint: string;
};

export type Snapshot = {
  health: Health | null;
  identities: Identity[];
  certificates: Certificate[];
  actions: ActionRequest[];
  incidents: Incident[];
  events: AuditEvent[];
  integrity: AuditIntegrity | null;
  protectedBoundary: ProtectedBoundary | null;
};

const API_ROOT = "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_ROOT}${path}`, {
    headers: { "Content-Type": "application/json", ...(options?.headers ?? {}) },
    ...options,
  });
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: string };
      detail = body.detail ?? detail;
    } catch {
      // Keep the HTTP error when the server did not return JSON.
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export async function loadSnapshot(): Promise<Snapshot> {
  const [health, identities, certificates, actions, incidents, events, integrity, protectedBoundary] = await Promise.all([
    request<Health>("/health"),
    request<Identity[]>("/identities"),
    request<Certificate[]>("/certificates"),
    request<ActionRequest[]>("/actions"),
    request<Incident[]>("/incidents"),
    request<AuditEvent[]>("/audit/events"),
    request<AuditIntegrity>("/audit/integrity"),
    request<ProtectedBoundary>("/protected-boundary"),
  ]);
  return { health, identities, certificates, actions, incidents, events, integrity, protectedBoundary };
}

export async function createIdentity(input: {
  name: string;
  kind: "service" | "agent";
  owner: string;
  purpose: string;
  allowed_actions: string[];
}): Promise<Identity> {
  return request<Identity>("/identities", { method: "POST", body: JSON.stringify(input) });
}

export async function issueCertificate(identityId: string, san: string): Promise<Certificate> {
  return request<Certificate>(`/identities/${identityId}/certificates`, {
    method: "POST",
    body: JSON.stringify({ sans: [san], validity: "24h" }),
  });
}

export async function quarantineIdentity(identityId: string): Promise<{ identity: Identity }> {
  return request<{ identity: Identity }>(`/identities/${identityId}/quarantine`, { method: "POST" });
}

export async function requestAction(
  identityId: string,
  input: { action: string; target: string; certificate_fingerprint: string },
): Promise<ActionRequest> {
  return request<ActionRequest>(`/identities/${identityId}/actions`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function approveAction(actionId: string): Promise<ActionRequest> {
  return request<ActionRequest>(`/actions/${actionId}/approve`, { method: "POST" });
}

export async function openCompromise(identityId: string, reason: string): Promise<Incident> {
  return request<Incident>("/incidents/compromise", {
    method: "POST",
    body: JSON.stringify({ identity_id: identityId, reason }),
  });
}

export async function recoverIncident(incidentId: string): Promise<{
  incident: Incident;
  identity: Identity;
  certificate: Certificate;
}> {
  return request(`/incidents/${incidentId}/recover`, { method: "POST" });
}
