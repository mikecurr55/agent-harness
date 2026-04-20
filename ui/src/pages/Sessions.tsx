import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Card } from "../components/Card";
import { StatusBadge } from "../components/StatusBadge";
import { useApi } from "../hooks/useApi";

export function Sessions() {
  const { data: sessions, loading, error, reload } = useApi(() => api.sessions.list());

  const [creating, setCreating] = useState(false);
  const [subject, setSubject] = useState("");
  const [scopes, setScopes] = useState("tool:read:*, llm:invoke");

  async function handleCreate() {
    setCreating(true);
    try {
      await api.sessions.create({
        principal_subject: subject,
        scopes: scopes.split(",").map((s) => s.trim()),
      });
      setSubject("");
      reload();
    } finally {
      setCreating(false);
    }
  }

  return (
    <div>
      <h2 className="text-xl font-semibold">Sessions</h2>
      <p className="mt-1 text-sm text-slate-500">Active and historical agent sessions</p>

      <Card className="mt-6">
        <h3 className="text-sm font-semibold text-slate-300">Create Session</h3>
        <div className="mt-3 flex flex-wrap gap-3">
          <input
            className="flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500/50"
            placeholder="Principal (e.g. user@company.com)"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
          />
          <input
            className="flex-[2] rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500/50"
            placeholder="Scopes (comma-separated)"
            value={scopes}
            onChange={(e) => setScopes(e.target.value)}
          />
          <button
            onClick={handleCreate}
            disabled={creating || !subject}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
          >
            {creating ? "Creating…" : "Create"}
          </button>
        </div>
      </Card>

      {loading && <p className="mt-4 text-slate-500">Loading…</p>}
      {error && <p className="mt-4 text-rose-400">{error}</p>}

      <div className="mt-4 space-y-2">
        {sessions?.map((s) => (
          <Link key={s.session_id} to={`/sessions/${s.session_id}`}>
            <Card className="flex items-center gap-4 transition-colors hover:border-slate-700">
              <div className="flex-1">
                <p className="text-sm font-medium text-slate-200">{s.principal}</p>
                <p className="mt-0.5 text-xs text-slate-500 font-mono">{s.agent_id.slice(0, 12)}…</p>
              </div>
              <div className="hidden text-xs text-slate-500 sm:block">
                {s.scopes.slice(0, 3).join(", ")}
                {s.scopes.length > 3 && ` +${s.scopes.length - 3}`}
              </div>
              <StatusBadge status={s.status} />
              <StatusBadge status={s.credential_valid ? "valid" : "expired"} />
            </Card>
          </Link>
        ))}
        {sessions?.length === 0 && (
          <p className="text-sm text-slate-500">No sessions yet. Create one above.</p>
        )}
      </div>
    </div>
  );
}
