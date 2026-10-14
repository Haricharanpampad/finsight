"use client";

import AppShell from "@/components/AppShell";
import TransactionManager from "@/components/TransactionManager";

export default function RevenuePage() {
  return (
    <AppShell>
      <h1 className="mb-1 text-2xl font-semibold">Revenue</h1>
      <p className="mb-6 text-sm text-slate-500">Record money coming in, by source (shop sales, online orders, wholesale…).</p>
      <TransactionManager type="revenue" />
    </AppShell>
  );
}
