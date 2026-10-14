import { pct } from "@/lib/format";

/**
 * A headline number. `delta` is a % change; `goodWhen` says whether going up is good
 * (revenue, profit) or bad (expenses), which decides the chip colour.
 */
export default function StatCard({ label, value, delta, goodWhen = "up", note }) {
  let tone = "bg-slate-100 text-slate-600";
  if (delta !== null && delta !== undefined && delta !== 0) {
    const good = goodWhen === "up" ? delta > 0 : delta < 0;
    tone = good ? "bg-emerald-50 text-emerald-700" : "bg-rose-50 text-rose-700";
  }
  return (
    <div className="card">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold tabular-nums md:text-3xl">{value}</p>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
        {delta !== undefined && <span className={`rounded-full px-2 py-0.5 font-medium ${tone}`}>{pct(delta)}</span>}
        {note && <span className="text-slate-500">{note}</span>}
      </div>
    </div>
  );
}
