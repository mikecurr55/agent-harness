import { api } from "../api";
import { Card } from "../components/Card";
import { useApi } from "../hooks/useApi";

export function Overrides() {
  const { data: overrides, loading, error, reload } = useApi(() => api.overrides.list());

  async function respond(requestId: string, decision: "approve" | "reject") {
    await api.overrides.respond(requestId, decision, "ui_operator");
    reload();
  }

  return (
    <div>
      <h2 className="text-xl font-semibold">Override Inbox</h2>
      <p className="mt-1 text-sm text-slate-500">
        Human-in-the-loop approval requests from agents
      </p>

      {loading && <p className="mt-4 text-slate-500">Loading…</p>}
      {error && <p className="mt-4 text-rose-400">{error}</p>}

      <div className="mt-6 space-y-3">
        {overrides?.map((o) => (
          <Card key={o.request_id} className="flex items-start gap-4">
            <div className="flex-1">
              <p className="text-sm font-medium text-slate-200">
                <span className="font-mono text-amber-400">{o.action}</span>
                {o.resource && <span className="text-slate-400"> on {o.resource}</span>}
              </p>
              <p className="mt-1 text-sm text-slate-400">{o.reason}</p>
              <div className="mt-2 flex gap-3 text-xs text-slate-600">
                <span>Agent: {o.agent_id.slice(0, 12)}…</span>
                <span>Session: {o.session_id.slice(0, 12)}…</span>
                <span>{new Date(o.timestamp).toLocaleString()}</span>
              </div>
              {Object.keys(o.context).length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {Object.entries(o.context).map(([k, v]) => (
                    <span key={k} className="rounded bg-slate-800 px-1.5 py-0.5 text-[11px] text-slate-500">
                      {k}={v}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <div className="flex shrink-0 gap-2">
              <button
                onClick={() => respond(o.request_id, "approve")}
                className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500"
              >
                Approve
              </button>
              <button
                onClick={() => respond(o.request_id, "reject")}
                className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-500"
              >
                Reject
              </button>
            </div>
          </Card>
        ))}
        {overrides?.length === 0 && (
          <Card className="text-center">
            <p className="text-sm text-slate-500">No pending override requests.</p>
          </Card>
        )}
      </div>
    </div>
  );
}
