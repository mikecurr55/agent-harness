import { Card } from "./Card";

type Props = {
  label: string;
  value: string | number;
  sub?: string;
  accent?: "emerald" | "rose" | "amber" | "slate";
};

const ACCENTS = {
  emerald: "text-emerald-400",
  rose: "text-rose-400",
  amber: "text-amber-400",
  slate: "text-slate-300",
};

export function MetricCard({ label, value, sub, accent = "slate" }: Props) {
  return (
    <Card>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${ACCENTS[accent]}`}>{value}</p>
      {sub && <p className="mt-0.5 text-xs text-slate-500">{sub}</p>}
    </Card>
  );
}
