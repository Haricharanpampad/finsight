"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import AppShell from "@/components/AppShell";
import ExpenseChart from "@/components/ExpenseChart";
import RevenueChart from "@/components/RevenueChart";
import StatCard from "@/components/StatCard";
import { api, getUser } from "@/services/api";
import { inr } from "@/lib/format";

const QUICK = ["Why is my profit lower this month?", "Which expense is increasing the most?", "What can I do to increase my profit?"];

const TONE = {
  warning: "border-amber-200 bg-amber-50",
  watch: "border-amber-100 bg-amber-50/60",
  info: "border-slate-200 bg-slate-50",
  good: "border-emerald-200 bg-emerald-50",
};

function Dashboard() {
  const router = useRouter();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [question, setQuestion] = useState("");
  const [greeting, setGreeting] = useState("Hello");
  const user = getUser();

  useEffect(() => {
    const h = new Date().getHours();
    setGreeting(h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening");
    api.dashboard().then(setData).catch((e) => setError(e.message));
  }, []);

  const ask = (q) => q.trim() && router.push(`/assistant?q=${encodeURIComponent(q.trim())}`);

  if (error) return <p className="card text-sm text-rose-700">{error}</p>;
  if (!data) return <p className="text-sm text-slate-500">Loading your business…</p>;

  const cmp = data.vs_last_period;
  const note = cmp.like_for_like ? "vs same days last month" : "vs previous month";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">{greeting}, {user?.name || "there"} 👋</h1>
        <p className="text-sm text-slate-500">
          Here&apos;s how {data.business} is doing — {data.month_label}, day {data.through_day} of {data.days_in_month}.
        </p>
      </div>

      <div className="rounded-2xl bg-gradient-to-br from-brand-600 to-indigo-800 p-5 text-white shadow-sm md:p-6">
        <p className="text-lg font-semibold">Ask FinSight anything…</p>
        <form onSubmit={(e) => { e.preventDefault(); ask(question); }} className="mt-3 flex gap-2">
          <input className="w-full rounded-lg border-0 px-3 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-white/60" placeholder="What was my profit this month?" value={question} onChange={(e) => setQuestion(e.target.value)} />
          <button className="rounded-lg bg-white px-4 py-2 text-sm font-medium text-brand-700 hover:bg-brand-50">Ask</button>
        </form>
        <div className="mt-3 flex flex-wrap gap-2">
          {QUICK.map((q) => (
            <button key={q} onClick={() => ask(q)} className="rounded-full bg-white/15 px-3 py-1 text-xs hover:bg-white/25">{q}</button>
          ))}
        </div>
      </div>

      {!data.has_data ? (
        <div className="card text-center">
          <p className="font-medium">No transactions yet</p>
          <p className="mt-1 text-sm text-slate-500">Add your first revenue and expenses and FinSight will start explaining your numbers.</p>
          <div className="mt-4 flex justify-center gap-3">
            <Link href="/revenue" className="btn">Add revenue</Link>
            <Link href="/expenses" className="btn-ghost">Add expense</Link>
          </div>
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Revenue" value={inr(data.revenue)} delta={cmp.change_pct.revenue} note={note} />
            <StatCard label="Expenses" value={inr(data.expenses)} delta={cmp.change_pct.expenses} goodWhen="down" note={note} />
            <StatCard label="Net profit" value={inr(data.profit)} delta={cmp.change_pct.profit} note={note} />
            <StatCard label="Profit margin" value={data.profit_margin === null ? "—" : `${data.profit_margin}%`} note={`${data.last_full_month.label}: ${data.last_full_month.profit_margin_pct ?? "—"}%`} />
          </div>

          <div className="card">
            <h2 className="mb-3 font-semibold">FinSight says</h2>
            <div className="space-y-3">
              {data.insights.map((r) => (
                <div key={r.title} className={`rounded-xl border p-4 ${TONE[r.severity] || TONE.info}`}>
                  <p className="text-sm font-medium">{r.severity === "warning" ? "⚠️ " : r.severity === "good" ? "✅ " : "💡 "}{r.title}</p>
                  <p className="mt-1 text-sm text-slate-700">{r.detail}</p>
                </div>
              ))}
            </div>
            <Link href="/assistant?q=Show%20me%20how" className="mt-3 inline-block text-sm font-medium text-brand-600 hover:underline">Show me how →</Link>
          </div>

          <div className="grid gap-6 lg:grid-cols-5">
            <div className="card lg:col-span-3">
              <h2 className="mb-1 font-semibold">Is my business growing?</h2>
              <p className="mb-3 text-sm text-slate-500">Revenue vs expenses over the last 6 months</p>
              <RevenueChart trend={data.trend} />
            </div>
            <div className="card lg:col-span-2">
              <h2 className="mb-1 font-semibold">Where is my money going?</h2>
              <p className="mb-3 text-sm text-slate-500">{data.month_label} so far</p>
              <ExpenseChart categories={data.top_expenses} growth={data.expense_growth} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default function DashboardPage() {
  return (
    <AppShell>
      <Dashboard />
    </AppShell>
  );
}
