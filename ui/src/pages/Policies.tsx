import { useState } from "react";
import { api, type PolicyRule } from "../api";
import { Card } from "../components/Card";
import { StatusBadge } from "../components/StatusBadge";
import { useApi } from "../hooks/useApi";

export function Policies() {
  const { data: policies, loading, error, reload } = useApi(() => api.policies.list());

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    id: "",
    description: "",
    action_pattern: "*",
    resource_pattern: "*",
    verdict: "deny",
    priority: 0,
  });

  async function handleCreate() {
    await api.policies.create({
      ...form,
      conditions: {},
    });
    setShowForm(false);
    setForm({ id: "", description: "", action_pattern: "*", resource_pattern: "*", verdict: "deny", priority: 0 });
    reload();
  }

  async function handleDelete(id: string) {
    await api.policies.delete(id);
    reload();
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Policies</h2>
          <p className="mt-1 text-sm text-slate-500">Policy-as-code rules governing agent actions</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500"
        >
          {showForm ? "Cancel" : "Add Policy"}
        </button>
      </div>

      {showForm && (
        <Card className="mt-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <input
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500/50"
              placeholder="Policy ID"
              value={form.id}
              onChange={(e) => setForm({ ...form, id: e.target.value })}
            />
            <input
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500/50 sm:col-span-2"
              placeholder="Description"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
            <input
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500/50"
              placeholder="Action pattern (e.g. tool:read:*)"
              value={form.action_pattern}
              onChange={(e) => setForm({ ...form, action_pattern: e.target.value })}
            />
            <input
              className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500/50"
              placeholder="Resource pattern"
              value={form.resource_pattern}
              onChange={(e) => setForm({ ...form, resource_pattern: e.target.value })}
            />
            <div className="flex gap-2">
              <select
                className="flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
                value={form.verdict}
                onChange={(e) => setForm({ ...form, verdict: e.target.value })}
              >
                <option value="allow">Allow</option>
                <option value="deny">Deny</option>
                <option value="escalate">Escalate</option>
              </select>
              <input
                className="w-20 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
                type="number"
                placeholder="Priority"
                value={form.priority}
                onChange={(e) => setForm({ ...form, priority: Number(e.target.value) })}
              />
            </div>
          </div>
          <button
            onClick={handleCreate}
            disabled={!form.id}
            className="mt-3 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
          >
            Create Policy
          </button>
        </Card>
      )}

      {loading && <p className="mt-4 text-slate-500">Loading…</p>}
      {error && <p className="mt-4 text-rose-400">{error}</p>}

      <div className="mt-4 space-y-2">
        {policies
          ?.sort((a, b) => b.priority - a.priority)
          .map((p) => (
            <Card key={p.id} className="flex items-center gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium text-slate-200">{p.id}</p>
                  <StatusBadge status={p.verdict} />
                  <span className="text-xs text-slate-600">priority {p.priority}</span>
                </div>
                {p.description && (
                  <p className="mt-0.5 text-xs text-slate-500">{p.description}</p>
                )}
                <div className="mt-1 flex gap-3 text-xs font-mono text-slate-600">
                  <span>action: {p.action_pattern}</span>
                  <span>resource: {p.resource_pattern}</span>
                </div>
              </div>
              <button
                onClick={() => handleDelete(p.id)}
                className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-rose-400 hover:bg-rose-500/10"
              >
                Delete
              </button>
            </Card>
          ))}
      </div>
    </div>
  );
}
