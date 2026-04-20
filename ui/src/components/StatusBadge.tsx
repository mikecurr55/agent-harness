const COLORS: Record<string, string> = {
  active: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  killed: "bg-rose-500/15 text-rose-400 border-rose-500/30",
  allow: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  deny: "bg-rose-500/15 text-rose-400 border-rose-500/30",
  escalate: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  pass: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  fail: "bg-rose-500/15 text-rose-400 border-rose-500/30",
  pending: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  valid: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  invalid: "bg-rose-500/15 text-rose-400 border-rose-500/30",
};

export function StatusBadge({ status }: { status: string }) {
  const color = COLORS[status.toLowerCase()] ?? "bg-slate-500/15 text-slate-400 border-slate-500/30";
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${color}`}>
      {status}
    </span>
  );
}
