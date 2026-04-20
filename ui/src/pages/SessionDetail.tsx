import { useParams } from "react-router-dom";
import { api } from "../api";
import { Card } from "../components/Card";
import { StatusBadge } from "../components/StatusBadge";
import { useApi } from "../hooks/useApi";

export function SessionDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: session, loading, error, reload } = useApi(
    () => api.sessions.get(id!),
    [id],
  );

  async function handleKill() {
    if (!id) return;
    await api.sessions.kill(id);
    reload();
  }

  if (loading) return <p className="text-slate-500">Loading session…</p>;
  if (error) return <p className="text-rose-400">{error}</p>;
  if (!session) return null;

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">{session.principal}</h2>
          <p className="mt-0.5 text-xs font-mono text-slate-500">
            Session: {session.session_id}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={session.status} />
          {session.status === "active" && (
            <button
              onClick={handleKill}
              className="rounded-lg bg-rose-600 px-4 py-2 text-sm font-semibold text-white hover:bg-rose-500"
            >
              Kill Switch
            </button>
          )}
        </div>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card>
          <h3 className="text-sm font-semibold text-slate-300">Identity & Credential</h3>
          <dl className="mt-3 space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-slate-500">Agent ID</dt>
              <dd className="font-mono text-slate-300">{session.agent_id.slice(0, 16)}…</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Credential</dt>
              <dd><StatusBadge status={session.credential_valid ? "valid" : "expired"} /></dd>
            </div>
            {session.credential_expires && (
              <div className="flex justify-between">
                <dt className="text-slate-500">Expires</dt>
                <dd className="text-slate-300">{new Date(session.credential_expires).toLocaleString()}</dd>
              </div>
            )}
          </dl>
        </Card>

        <Card>
          <h3 className="text-sm font-semibold text-slate-300">Scopes & Limits</h3>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {session.scopes.map((s) => (
              <span key={s} className="rounded-md bg-slate-800 px-2 py-0.5 text-xs font-mono text-emerald-400">
                {s}
              </span>
            ))}
          </div>
          <dl className="mt-3 space-y-1 text-sm">
            {Object.entries(session.limits).map(([k, v]) => (
              <div key={k} className="flex justify-between">
                <dt className="text-slate-500">{k.replace(/_/g, " ")}</dt>
                <dd className="text-slate-300">{v}</dd>
              </div>
            ))}
          </dl>
        </Card>

        <Card className="lg:col-span-2">
          <h3 className="text-sm font-semibold text-slate-300">Delegation Chain</h3>
          {session.delegation_chain.length === 0 ? (
            <p className="mt-2 text-sm text-slate-500">No delegation links.</p>
          ) : (
            <div className="mt-3 space-y-2">
              {session.delegation_chain.map((link, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 rounded-lg bg-slate-950/50 px-3 py-2 text-sm"
                >
                  <span className="font-mono text-slate-400">{link.delegator.slice(0, 8)}…</span>
                  <span className="text-slate-600">→</span>
                  <span className="font-mono text-emerald-400">{link.delegate.slice(0, 8)}…</span>
                  <span className="ml-auto text-xs text-slate-600">
                    {link.scopes.join(", ")}
                  </span>
                  <span className="font-mono text-xs text-slate-700">{link.hash}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
