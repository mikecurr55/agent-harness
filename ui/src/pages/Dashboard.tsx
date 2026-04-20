import { api } from "../api";
import { MetricCard } from "../components/MetricCard";
import { StatusBadge } from "../components/StatusBadge";
import { useApi } from "../hooks/useApi";

export function Dashboard() {
  const { data, loading, error } = useApi(() => api.dashboard());

  if (loading) return <p className="text-slate-500">Loading dashboard…</p>;
  if (error) return <p className="text-rose-400">{error}</p>;
  if (!data) return null;

  return (
    <div>
      <h2 className="text-xl font-semibold">Dashboard</h2>
      <p className="mt-1 text-sm text-slate-500">System overview and health status</p>

      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        <MetricCard
          label="Active Sessions"
          value={data.active_sessions}
          sub={`${data.total_sessions} total`}
          accent="emerald"
        />
        <MetricCard
          label="Killed Sessions"
          value={data.killed_sessions}
          accent={data.killed_sessions > 0 ? "rose" : "slate"}
        />
        <MetricCard
          label="Pending Overrides"
          value={data.pending_overrides}
          accent={data.pending_overrides > 0 ? "amber" : "slate"}
        />
        <MetricCard
          label="Policy Rules"
          value={data.policy_rules}
        />
        <MetricCard
          label="Audit Entries"
          value={data.audit_entries}
          sub={
            <span className="inline-flex items-center gap-1.5">
              Chain: <StatusBadge status={data.audit_chain_valid ? "valid" : "invalid"} />
            </span> as unknown as string
          }
        />
        <MetricCard
          label="Design Changes"
          value={data.design_changes}
          sub={
            <span className="inline-flex items-center gap-1.5">
              Chain: <StatusBadge status={data.design_chain_valid ? "valid" : "invalid"} />
            </span> as unknown as string
          }
        />
      </div>
    </div>
  );
}
