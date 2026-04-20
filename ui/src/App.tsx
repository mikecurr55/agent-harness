import { NavLink, Route, Routes } from "react-router-dom";
import { Dashboard } from "./pages/Dashboard";
import { Sessions } from "./pages/Sessions";
import { SessionDetail } from "./pages/SessionDetail";
import { AuditTrail } from "./pages/AuditTrail";
import { Overrides } from "./pages/Overrides";
import { Policies } from "./pages/Policies";
import { DesignLog } from "./pages/DesignLog";

const NAV = [
  { to: "/", label: "Dashboard" },
  { to: "/sessions", label: "Sessions" },
  { to: "/audit", label: "Audit Trail" },
  { to: "/overrides", label: "Overrides" },
  { to: "/policies", label: "Policies" },
  { to: "/design-log", label: "Design Log" },
];

function navClass({ isActive }: { isActive: boolean }) {
  return `px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
    isActive
      ? "bg-emerald-600/20 text-emerald-400"
      : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
  }`;
}

export function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center gap-6 px-4 py-3">
          <h1 className="text-lg font-bold tracking-tight text-slate-100">
            Agent Harness
          </h1>
          <nav className="flex gap-1">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} end={n.to === "/"} className={navClass}>
                {n.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/sessions" element={<Sessions />} />
          <Route path="/sessions/:id" element={<SessionDetail />} />
          <Route path="/audit" element={<AuditTrail />} />
          <Route path="/overrides" element={<Overrides />} />
          <Route path="/policies" element={<Policies />} />
          <Route path="/design-log" element={<DesignLog />} />
        </Routes>
      </main>

      <footer className="border-t border-slate-800 py-3 text-center text-xs text-slate-600">
        Agent Harness v0.1.0 — Secure, governed agent orchestration
      </footer>
    </div>
  );
}
