"use client";

import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { compactInr, inr } from "@/lib/format";

/** Revenue vs expenses per month, with profit as a line. `trend` comes from /api/dashboard. */
export default function RevenueChart({ trend }) {
  const data = trend.map((t) => ({ ...t, name: t.partial ? `${t.label}*` : t.label }));
  return (
    <div>
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} stroke="#94a3b8" />
            <YAxis tickFormatter={compactInr} tick={{ fontSize: 12 }} stroke="#94a3b8" width={56} />
            <Tooltip formatter={(v) => inr(v)} />
            <Legend />
            <Bar dataKey="revenue" name="Revenue" fill="#4f46e5" radius={[4, 4, 0, 0]} />
            <Bar dataKey="expenses" name="Expenses" fill="#f59e0b" radius={[4, 4, 0, 0]} />
            <Line dataKey="profit" name="Profit" stroke="#10b981" strokeWidth={2.5} dot={{ r: 3 }} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      {data.some((d) => d.partial) && <p className="mt-2 text-xs text-slate-500">* Current month so far (not a full month yet).</p>}
    </div>
  );
}
