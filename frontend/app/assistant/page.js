"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import AppShell from "@/components/AppShell";
import ChatBox from "@/components/ChatBox";

function Assistant() {
  const q = useSearchParams().get("q") || undefined;
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Ask FinSight</h1>
        <p className="text-sm text-slate-500">Your business copilot: it looks up your real numbers, then explains what they mean.</p>
      </div>
      <ChatBox initialQuestion={q} />
    </div>
  );
}

export default function AssistantPage() {
  return (
    <AppShell>
      <Suspense fallback={<p className="text-sm text-slate-500">Loading…</p>}>
        <Assistant />
      </Suspense>
    </AppShell>
  );
}
