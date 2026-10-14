"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, getToken, saveSession } from "@/services/api";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "", email: "", password: "", business_name: "", business_type: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (getToken()) router.replace("/dashboard");
  }, [router]);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function submit(e, override) {
    e?.preventDefault();
    setBusy(true);
    setError("");
    try {
      const creds = override || form;
      const session =
        mode === "login" || override
          ? await api.login({ email: creds.email, password: creds.password })
          : await api.register({ ...form, business_type: form.business_type || "General" });
      saveSession(session);
      router.replace("/dashboard");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <span className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-brand-600 text-xl font-bold text-white">F</span>
          <h1 className="text-2xl font-semibold">FinSight</h1>
          <p className="mt-1 text-sm text-slate-500">Talk to your business numbers. Get answers, not spreadsheets.</p>
        </div>

        <form onSubmit={submit} className="card space-y-4">
          <div className="grid grid-cols-2 gap-1 rounded-lg bg-slate-100 p-1 text-sm font-medium">
            {["login", "register"].map((m) => (
              <button type="button" key={m} onClick={() => { setMode(m); setError(""); }} className={`rounded-md py-1.5 ${mode === m ? "bg-white shadow-sm" : "text-slate-500"}`}>
                {m === "login" ? "Log in" : "Create account"}
              </button>
            ))}
          </div>

          {mode === "register" && (
            <>
              <div>
                <label className="label">Your name</label>
                <input className="input" value={form.name} onChange={set("name")} required />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="label">Business name</label>
                  <input className="input" value={form.business_name} onChange={set("business_name")} required />
                </div>
                <div>
                  <label className="label">Business type</label>
                  <input className="input" value={form.business_type} onChange={set("business_type")} placeholder="Retail, Cafe…" />
                </div>
              </div>
            </>
          )}
          <div>
            <label className="label">Email</label>
            <input type="email" className="input" value={form.email} onChange={set("email")} required autoComplete="email" />
          </div>
          <div>
            <label className="label">Password</label>
            <input type="password" className="input" value={form.password} onChange={set("password")} required minLength={mode === "register" ? 8 : undefined} maxLength={72} autoComplete={mode === "login" ? "current-password" : "new-password"} />
            {mode === "register" && <p className="mt-1 text-xs text-slate-500">At least 8 characters.</p>}
          </div>

          {error && <p className="rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>}
          <button className="btn w-full" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Log in" : "Create account"}</button>
        </form>

        <p className="mt-4 text-center text-sm text-slate-500">
          Just exploring?{" "}
          <button type="button" className="font-medium text-brand-600 hover:underline" onClick={() => { setMode("login"); submit(null, { email: "demo@finsight.app", password: "demo12345" }); }}>
            Try the demo account
          </button>
          <span className="block text-xs">(run <code>python seed.py</code> in the backend first)</span>
        </p>
      </div>
    </div>
  );
}
