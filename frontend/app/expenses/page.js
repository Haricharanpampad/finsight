"use client";

import AppShell from "@/components/AppShell";
import TransactionManager from "@/components/TransactionManager";

export default function ExpensesPage() {
  return (
    <AppShell>
      <h1 className="mb-1 text-2xl font-semibold">Expenses</h1>
      <p className="mb-6 text-sm text-slate-500">Record what you spend. Categories help FinSight explain where your money goes.</p>
      <TransactionManager type="expense" />
    </AppShell>
  );
}
