const BASE = "/api";

async function request<T>(path: string, opts?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    headers: { "content-type": "application/json", ...opts?.headers },
    ...opts,
  });
  if (!r.ok) {
    const text = await r.text();
    throw new Error(`${r.status}: ${text}`);
  }
  return r.json();
}

export type DashboardData = {
  total_sessions: number;
  active_sessions: number;
  killed_sessions: number;
  pending_overrides: number;
  audit_entries: number;
  audit_chain_valid: boolean;
  design_changes: number;
  design_chain_valid: boolean;
  policy_rules: number;
};

export type SessionSummary = {
  session_id: string;
  agent_id: string;
  principal: string;
  scopes: string[];
  status: string;
  credential_valid: boolean;
  credential_expires: string | null;
};

export type SessionDetail = SessionSummary & {
  limits: Record<string, string>;
  delegation_chain: {
    delegator: string;
    delegate: string;
    scopes: string[];
    timestamp: string;
    hash: string;
  }[];
  pending_overrides: {
    request_id: string;
    action: string;
    resource: string;
    reason: string;
    timestamp: string;
  }[];
};

export type AuditEntry = {
  entry_id: string;
  timestamp: string;
  event_type: string;
  agent_id: string;
  session_id: string;
  action: string;
  resource: string;
  detail: string;
  entry_hash: string;
  previous_hash: string;
};

export type OverrideRequest = {
  request_id: string;
  session_id: string;
  agent_id: string;
  action: string;
  resource: string;
  reason: string;
  context: Record<string, string>;
  timestamp: string;
};

export type PolicyRule = {
  id: string;
  description: string;
  action_pattern: string;
  resource_pattern: string;
  conditions: Record<string, string>;
  verdict: string;
  priority: number;
};

export type DesignChange = {
  change_id: string;
  timestamp: string;
  change_type: string;
  changed_by: string;
  component: string;
  reason: string;
  change_hash: string;
};

export const api = {
  dashboard: () => request<DashboardData>("/dashboard"),

  sessions: {
    list: () => request<SessionSummary[]>("/sessions"),
    get: (id: string) => request<SessionDetail>(`/sessions/${id}`),
    create: (body: {
      principal_subject: string;
      scopes: string[];
      max_tool_calls?: number;
      max_dollar_spend?: string;
      credential_ttl_minutes?: number;
    }) => request<SessionSummary>("/sessions", { method: "POST", body: JSON.stringify(body) }),
    kill: (id: string, reason?: string) =>
      request(`/sessions/${id}/kill?reason=${encodeURIComponent(reason ?? "Manual kill")}`, {
        method: "POST",
      }),
  },

  audit: {
    list: (params?: { session_id?: string; event_type?: string; limit?: number }) => {
      const q = new URLSearchParams();
      if (params?.session_id) q.set("session_id", params.session_id);
      if (params?.event_type) q.set("event_type", params.event_type);
      if (params?.limit) q.set("limit", String(params.limit));
      return request<AuditEntry[]>(`/audit?${q}`);
    },
    verify: (session_id?: string) => {
      const q = session_id ? `?session_id=${session_id}` : "";
      return request<{ valid: boolean; entries_checked: number }>(`/audit/verify${q}`);
    },
    designChanges: () => request<DesignChange[]>("/audit/design-changes"),
  },

  overrides: {
    list: () => request<OverrideRequest[]>("/overrides"),
    respond: (id: string, decision: string, decided_by: string, modification?: string) =>
      request(`/overrides/${id}/respond`, {
        method: "POST",
        body: JSON.stringify({ decision, decided_by, modification }),
      }),
  },

  policies: {
    list: () => request<PolicyRule[]>("/policies"),
    create: (rule: Omit<PolicyRule, "conditions"> & { conditions?: Record<string, string> }) =>
      request("/policies", { method: "POST", body: JSON.stringify(rule) }),
    update: (id: string, rule: Omit<PolicyRule, "id">) =>
      request(`/policies/${id}`, { method: "PUT", body: JSON.stringify({ id, ...rule }) }),
    delete: (id: string) => request(`/policies/${id}`, { method: "DELETE" }),
  },
};
