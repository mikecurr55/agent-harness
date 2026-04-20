import { api } from "../api";
import { Card } from "../components/Card";
import { useApi } from "../hooks/useApi";

export function DesignLog() {
  const { data: changes, loading, error } = useApi(() => api.audit.designChanges());

  return (
    <div>
      <h2 className="text-xl font-semibold">Design Change Log</h2>
      <p className="mt-1 text-sm text-slate-500">
        Hash-chained log of all configuration and orchestration changes
      </p>

      {loading && <p className="mt-4 text-slate-500">Loading…</p>}
      {error && <p className="mt-4 text-rose-400">{error}</p>}

      <div className="mt-6 space-y-2">
        {changes?.map((c) => (
          <Card key={c.change_id} className="flex items-start gap-4 !p-3">
            <div className="w-36 shrink-0">
              <p className="text-xs text-slate-500">
                {new Date(c.timestamp).toLocaleString()}
              </p>
              <p className="mt-0.5 text-xs font-medium text-amber-400">
                {c.change_type.replace(/_/g, " ")}
              </p>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-slate-300">
                <span className="font-mono text-slate-400">{c.component}</span>
              </p>
              {c.reason && (
                <p className="mt-0.5 text-xs text-slate-500">{c.reason}</p>
              )}
              <p className="mt-0.5 text-xs text-slate-600">by {c.changed_by}</p>
            </div>
            <div className="shrink-0">
              <p className="font-mono text-[10px] text-slate-700">{c.change_hash}</p>
            </div>
          </Card>
        ))}
        {changes?.length === 0 && (
          <Card className="text-center">
            <p className="text-sm text-slate-500">No design changes recorded yet.</p>
          </Card>
        )}
      </div>
    </div>
  );
}
