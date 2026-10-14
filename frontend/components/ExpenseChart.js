"use client";

import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { compactInr, inr } from "@/lib/format";

/**
 * "Where is my money going?" - expense categories, highlighted in amber when they are rising
 * quickly. `growth` (optional) is the category_growth list from the API.
 */
export default function ExpenseChart({ categories, growth = [] }) {
  const rising = new Map(growth.filter((g) => g.change_pct !== null && g.change_pct >= 10 && g.change > 0).map((g) => [g.category, g.change_pct]));
  const data = categories.map((c) => ({ ...c, rising: rising.has(c.category), growthPct: rising.get(c.category) }));
  if (!data.length) return <p className="text-sm text-slate-500">No expenses recorded yet.</p>;
  return (
    <div>
      <div style={{ height: Math.max(180, data.length * 44) }} className="w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 0, right: 16, left: 0, bottom: 0 }}>
            <XAxis type="number" tickFormatter={compactInr} tick={{ fontSize: 12 }} stroke="#94a3b8" />
            <YAxis type="category" dataKey="category" width={90} tick={{ fontSize: 12 }} stroke="#94a3b8" />
            <Tooltip
              formatter={(v, _n, item) => [inr(v) + (item.payload.rising ? ` (up ${item.payload.growthPct}%)` : ""), "Spent"]}
              cursor={{ fill: "#f1f5f9" }}
            />
            <Bar dataKey="amount" radius={[0, 4, 4, 0]}>
              {data.map((d) => (
                <Cell key={d.category} fill={d.rising ? "#f59e0b" : "#6366f1"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      {data.some((d) => d.rising) && (
        <p className="mt-2 text-xs text-slate-500">
          <span className="mr-1 inline-block h-2 w-2 rounded-full bg-amber-500" /> Amber = rising 10%+ compared with the same days last month.
        </p>
      )}
    </div>
  );
}
