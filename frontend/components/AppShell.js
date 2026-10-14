"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { clearSession, getToken, getUser } from "@/services/api";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/assistant", label: "Ask FinSight" },
  { href: "/expenses", label: "Expenses" },
  { href: "/revenue", label: "Revenue" },
  { href: "/analytics", label: "Analytics" },
];

/** Page frame: redirects to /login when signed out, and shows the sidebar / top navigation. */
export default function AppShell({ children }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    setUser(getUser());
    setReady(true);
  }, [router]);

  function logout() {
    clearSession();
    router.replace("/login");
  }

  if (!ready) return <div className="p-10 text-sm text-slate-500">Loading…</div>;

  const links = NAV.map((n) => {
    const active = pathname === n.href;
    return (
      <Link
        key={n.href}
        href={n.href}
        className={`whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition ${
          active ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100"
        }`}
      >
        {n.label}
      </Link>
    );
  });

  return (
    <div className="min-h-screen md:flex">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-slate-200 bg-white p-4 md:flex">
        <div className="mb-6 flex items-center gap-2 px-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-sm font-bold text-white">F</span>
          <span className="text-lg font-semibold">FinSight</span>
        </div>
        <nav className="flex flex-col gap-1">{links}</nav>
        <div className="mt-auto border-t border-slate-100 pt-4">
          <p className="truncate px-2 text-sm font-medium">{user?.name}</p>
          <p className="truncate px-2 text-xs text-slate-500">{user?.business?.business_name}</p>
          <button onClick={logout} className="btn-ghost mt-3 w-full">Log out</button>
        </div>
      </aside>

      <div className="flex-1">
        <header className="flex items-center gap-2 overflow-x-auto border-b border-slate-200 bg-white px-3 py-2 md:hidden">
          <span className="mr-2 font-semibold text-brand-700">FinSight</span>
          {links}
          <button onClick={logout} className="btn-ghost ml-auto">Log out</button>
        </header>
        <main className="mx-auto max-w-6xl p-4 md:p-8">{children}</main>
      </div>
    </div>
  );
}
