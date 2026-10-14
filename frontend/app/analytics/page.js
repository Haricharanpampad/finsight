"use client";

import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import ExpenseChart from "@/components/ExpenseChart";
import RevenueChart from "@/components/RevenueChart";
import { api } from "@/services/api";
import { inr, monthLabel, pct } from "@/lib/format";

function WhatIf() {
  const [v, setV] = useState({ price_change_pct: "", sales_change_pct: "", expense_change_amount: "", category: "" });
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setV((s) => ({ ...s, [k]: e.target.value }));

  async function run(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      setResult(
        await api.scenario({
          price_change_pct: Number(v.price_change_pct) || 0,
          sales_change_pct: Number(v.sales_change_pct) || 0,
          expense_change_amount: Number(v.expense_change_amount) || 0,
          category: v.category.trim() || null,
        })
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h2 className="font-semibold">What-if simulator</h2>
      <p className="mb-4 text-sm text-slate-500">Try a change and see what happens to your monthly profit. Use negative numbers to reduce.</p>
      <form onSubmit={run} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <label className="label">Price change (%)</label>
          <input type="number" step="any" className="input" value={v.price_change_pct} onChange={set("price_change_pct")} placeholder="5" />
        </div>
        <div>
          <label className="label">Sales volume change (%)</label>
          <input type="number" step="any" className="input" value={v.sales_change_pct} onChange={set("sales_change_pct")} placeholder="10" />
        </div>
        <div>
          <label className="label">Expense change (₹)</label>
          <input type="number" step="any" className="input" value={v.expense_change_amount} onChange={set("expense_change_amount")} placeholder="-5000" />
        </div>
        <div>
          <label className="label">…for category (optional)</label>
          <input className="input" value={v.category} onChange={set("category")} placeholder="Marketing" />
        </div>
        <div className="sm:col-span-2 lg:col-span-4">
          <button className="btn" disabled={busy}>{busy ? "Calculating…" : "Calculate"}</button>
          {error && <span className="ml-3 text-sm text-rose-600">{error}</span>}
        </div>
      </form>

      {result && (
        <div className="mt-5 rounded-xl bg-slate-50 p-4 text-sm">
          <p>
            Based on {monthLabel(result.basis_month)}: profit goes from <b>{inr(result.baseline.profit)}</b> to{" "}
            <b>{inr(result.projected.profit)}</b>{" "}
            <span className={result.profit_change >= 0 ? "text-emerald-700" : "text-rose-700"}>
              ({result.profit_change >= 0 ? "+" : "-"}{inr(Math.abs(result.profit_change))})
            </span>
            .
          </p>
          <p className="mt-2 text-xs text-slate-500">Projection, not a prediction. {result.assumptions.join(" ")}</p>
        </div>
      )}
    </div>
  );
}

function Analytics() {
  const [dash, setDash] = useState(null);
  const [exp, setExp] = useState(null);
  const [recs, setRecs] = useState(null);
  const [fc, setFc] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.dashboard(), api.expenseAnalytics(), api.insights(), api.forecast()])
      .then(([d, e, r, f]) => {
        setDash(d);
        setExp(e);
        setRecs(r.recommendations);
        setFc(f);
      })
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <p className="card text-sm text-rose-700">{error}</p>;
  if (!dash) return <p className="text-sm text-slate-500">Loading analytics…</p>;

  const growth = exp.growth.filter((g) => g.current || g.previous);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Analytics</h1>
        <p className="text-sm text-slate-500">Each section answers one question about your business.</p>
      </div>

      <div className="card">
        <h2 className="mb-1 font-semibold">How has my profit changed month by month?</h2>
        <RevenueChart trend={dash.trend} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card">
          <h2 className="mb-1 font-semibold">Why did my expenses change?</h2>
          <p className="mb-3 text-sm text-slate-500">{monthLabel(exp.month)} vs the same period last month</p>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-slate-500">
                <tr><th className="py-2 pr-3">Category</th><th className="py-2 pr-3 text-right">Now</th><th className="py-2 pr-3 text-right">Before</th><th className="py-2 text-right">Change</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {growth.map((g) => (
                  <tr key={g.category}>
                    <td className="py-2 pr-3 font-medium">{g.category}</td>
                    <td className="py-2 pr-3 text-right tabular-nums">{inr(g.current)}</td>
                    <td className="py-2 pr-3 text-right tabular-nums text-slate-500">{inr(g.previous)}</td>
                    <td className={`py-2 text-right tabular-nums ${g.change > 0 ? "text-rose-600" : g.change < 0 ? "text-emerald-600" : "text-slate-500"}`}>
                      {g.change > 0 ? "+" : ""}{inr(g.change)} <span className="text-xs">({pct(g.change_pct)})</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="card">
          <h2 className="mb-1 font-semibold">Where is my money going?</h2>
          <p className="mb-3 text-sm text-slate-500">{monthLabel(exp.month)}</p>
          <ExpenseChart categories={exp.categories} growth={exp.growth} />
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card">
          <h2 className="mb-1 font-semibold">What could next month look like?</h2>
          {fc?.available ? (
            <>
              <p className="mt-2 text-3xl font-semibold tabular-nums">{inr(fc.estimate)}</p>
              <p className="text-sm text-slate-500">Forecast revenue for {monthLabel(fc.target_month)} · likely range {inr(fc.low)} to {inr(fc.high)}</p>
              <p className="mt-3 text-xs text-slate-500">Forecast, not a guarantee — {fc.method}.</p>
            </>
          ) : (
            <p className="mt-2 text-sm text-slate-500">{fc?.reason}</p>
          )}
        </div>
        <div className="card">
          <h2 className="mb-3 font-semibold">What should I do next?</h2>
          <div className="space-y-4">
            {recs.map((r) => (
              <div key={r.title}>
                <p className="text-sm font-medium">{r.title}</p>
                <p className="text-sm text-slate-600">{r.detail}</p>
                {r.steps?.length > 0 && (
                  <ol className="mt-1 list-decimal pl-5 text-sm text-slate-600">
                    {r.steps.map((s) => <li key={s}>{s}</li>)}
                  </ol>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      <WhatIf />
    </div>
  );
}

export default function AnalyticsPage() {
  return (
    <AppShell>
      <Analytics />
    </AppShell>
  );
}
