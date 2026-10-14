"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { getToken } from "@/services/api";

export default function Home() {
  const router = useRouter();
  useEffect(() => {
    router.replace(getToken() ? "/dashboard" : "/login");
  }, [router]);
  return <div className="p-10 text-sm text-slate-500">Loading…</div>;
}
