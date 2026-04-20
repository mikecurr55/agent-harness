import { useState } from "react";
import { api } from "../api";
import { Card } from "../components/Card";
import { StatusBadge } from "../components/StatusBadge";
import { useApi } from "../hooks/useApi";

const EVENT_COLORS: Record<string, string> = {
  policy_denied: "rose",
  kill_switch: "rose",
  limit_exceeded: "rose",
  action_failed: "rose",
  deviation_detected: "amber",
  human_override: "amber",
};

export function AuditTrail() {
  const [sessionFilter, setSessionFilter] = useState("");
  const [eventFilter, setEventFilter] = useState("");

  const { data: entries, loading, error, reload } = useApi(
    () => api.audit.list({
      session_id: sessionFilter || undefined,
      event_type: eventFilter || undefined,
      limit: 200,
    }),
    [sessionFilter, eventFilter],
  );

  const { data: verification } = useApi(() => api.audit.verify());

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Audit Trail</h2>
          <p className="mt-1 text-sm text-slate-500">Tamper-evident log of all agent activity</p>
        </div>
        {verification && (
          <div className="flex items-center gap-2 text-sm">
            <span className="text-slate-500">Chain integrity:</span>
            <StatusBadge status={verification.valid ? "valid" : "invalid"} />
            <span className="text-slate-600">{verification.entries_checked} entries</span>
          </div>
        )}
      </div>

      <div className="mt-4 flex gap-3">
        <input
          className="flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500/50"
          placeholder="Filter by session ID…"
          value={sessionFilter}
          onChange={(e) => setSessionFilter(e.target.value)}
        />
        <select
          className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500/50"
          value={eventFilter}
          onChange={(e) => setEventFilter(e.target.value)}
        >
          <option value="">All events</option>
          <option value="agent_created">Agent created</option>
          <option value="credential_issued">Credential issued</option>
          <option value="policy_evaluated">Policy evaluated</option>
          <option value="policy_denied">Policy denied</option>
          <option value="action_started">Action started</option>
          <option value="action_completed">Action completed</option>
          <option value="action_failed">Action failed</option>
          <option value="deviation_detected">Deviation detected</option>
          <option value="human_override">Human override</option>
          <option value="kill_switch">Kill switch</option>
          <option value="tool_call">Tool call</option>
          <option value="llm_call">LLM call</option>
        </select>
        <button
          onClick={reload}
          className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-400 hover:bg-slate-800"
        >
          Refresh
        </button>
      </div>

      {loading && <p className="mt-4 text-slate-500">Loading…</p>}
      {error && <p className="mt-4 text-rose-400">{error}</p>}

      <div className="mt-4 space-y-1.5">
        {entries?.map((e) => {
          const accent = EVENT_COLORS[e.event_type];
          return (
            <Card key={e.entry_id} className="flex items-start gap-4 !p-3">
              <div className="w-36 shrink-0">
                <p className="text-xs text-slate-500">
                  {new Date(e.timestamp).toLocaleTimeString()}
                </p>
                <StatusBadge status={accent ? e.event_type.replace(/_/g, " ") : e.event_type.replace(/_/g, " ")} />
              </div>
              <div className="flex-1 min-w-0">
                {e.action && (
                  <p className="text-sm text-slate-300">
                    <span className="font-mono text-emerald-400">{e.action}</span>
                    {e.resource && <span className="text-slate-500"> on {e.resource}</span>}
                  </p>
                )}
                {e.detail && (
                  <p className="mt-0.5 truncate text-xs text-slate-500">{e.detail}</p>
                )}
              </div>
              <div className="shrink-0 text-right">
                <p className="font-mono text-[10px] text-slate-700">{e.entry_hash}</p>
                {e.previous_hash && (
                  <p className="font-mono text-[10px] text-slate-800">← {e.previous_hash}</p>
                )}
              </div>
            </Card>
          );
        })}
        {entries?.length === 0 && (
          <p className="text-sm text-slate-500">No audit entries found.</p>
        )}
      </div>
    </div>
  );
}
