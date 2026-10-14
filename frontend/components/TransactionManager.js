"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/services/api";
import { inr, thisMonth, todayISO } from "@/lib/format";
import FileUploader from "@/components/FileUploader";

const METHODS = ["UPI", "Cash", "Card", "Bank transfer", "Other"];

/** Add / edit / delete expenses or revenue. `type` is "expense" or "revenue". */
export default function TransactionManager({ type }) {
  const isExpense = type === "expense";
  const noun = isExpense ? "expense" : "revenue";
  const categoryLabel = isExpense ? "Category" : "Source";

  const blank = { transaction_date: todayISO(), amount: "", category: "", description: "", payment_method: "UPI" };
  const [form, setForm] = useState(blank);
  const [editingId, setEditingId] = useState(null);
  const [items, setItems] = useState([]);
  const [categories, setCategories] = useState([]);
  const [month, setMonth] = useState(thisMonth());
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showUploader, setShowUploader] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [list, cats] = await Promise.all([api.listTransactions({ type, month }), api.categories(type)]);
      setItems(list);
      setCategories(cats);
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [type, month]);

  useEffect(() => {
    load();
  }, [load]);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function submit(e) {
    e.preventDefault();
    const amount = Number(form.amount);
    if (!(amount > 0)) return setError("Enter an amount greater than zero.");
    if (!form.category.trim()) return setError(`Choose or type a ${categoryLabel.toLowerCase()}.`);
    setSaving(true);
    setError("");
    const payload = { type, amount, category: form.category.trim(), description: form.description.trim(), transaction_date: form.transaction_date, payment_method: form.payment_method };
    try {
      if (editingId) await api.updateTransaction(editingId, payload);
      else await api.createTransaction(payload);
      setForm({ ...blank, transaction_date: form.transaction_date });
      setEditingId(null);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  function startEdit(t) {
    setEditingId(t.id);
    setForm({ transaction_date: t.transaction_date, amount: String(t.amount), category: t.category, description: t.description, payment_method: t.payment_method || "UPI" });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function remove(t) {
    if (!window.confirm(`Delete this ${noun} of ${inr(t.amount)} (${t.category})?`)) return;
    try {
      await api.deleteTransaction(t.id);
      if (editingId === t.id) {
        setEditingId(null);
        setForm(blank);
      }
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  const total = items.reduce((s, t) => s + t.amount, 0);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">{isExpense ? "Expense Management" : "Revenue Management"}</h2>
          <p className="text-xs text-slate-500">Record transactions manually or bulk import from your bank statement.</p>
        </div>
        <button
          type="button"
          onClick={() => setShowUploader((s) => !s)}
          className={`btn-ghost text-xs flex items-center gap-2 ${showUploader ? "bg-slate-100 border-slate-400 font-semibold text-brand-700" : ""}`}
        >
          <svg className="w-4 h-4 text-brand-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          {showUploader ? "Close Bulk Import" : "Bulk Import (CSV / Excel / PDF)"}
        </button>
      </div>

      {showUploader && (
        <FileUploader
          defaultType={type}
          availableCategories={categories}
          onSuccess={() => {
            load();
          }}
          onClose={() => setShowUploader(false)}
        />
      )}

      <form onSubmit={submit} className="card">
        <h2 className="mb-4 font-semibold">{editingId ? `Edit ${noun}` : `Add single ${noun} manually`}</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <div>
            <label className="label">Date</label>
            <input type="date" className="input" value={form.transaction_date} onChange={set("transaction_date")} required />
          </div>
          <div>
            <label className="label">Amount (₹)</label>
            <input type="number" min="0" step="0.01" className="input" value={form.amount} onChange={set("amount")} placeholder="3500" required />
          </div>
          <div>
            <label className="label">{categoryLabel}</label>
            <input list={`${type}-categories`} className="input" value={form.category} onChange={set("category")} placeholder={isExpense ? "Marketing" : "Retail sales"} required />
            <datalist id={`${type}-categories`}>
              {categories.map((c) => (
                <option key={c} value={c} />
              ))}
            </datalist>
          </div>
          <div>
            <label className="label">Description</label>
            <input className="input" value={form.description} onChange={set("description")} placeholder="Instagram advertising" maxLength={255} />
          </div>
          <div>
            <label className="label">Payment method</label>
            <select className="input" value={form.payment_method} onChange={set("payment_method")}>
              {METHODS.map((m) => (
                <option key={m}>{m}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <button className="btn" disabled={saving}>{saving ? "Saving…" : editingId ? "Save changes" : `Add ${noun}`}</button>
          {editingId && (
            <button type="button" className="btn-ghost" onClick={() => { setEditingId(null); setForm(blank); }}>Cancel</button>
          )}
          {error && <p className="text-sm text-rose-600">{error}</p>}
        </div>
      </form>

      <div className="card">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-semibold">
            {isExpense ? "Expenses" : "Revenue"} <span className="ml-2 text-sm font-normal text-slate-500">{items.length} entries · {inr(total)}</span>
          </h2>
          <input type="month" className="input w-auto" value={month} onChange={(e) => setMonth(e.target.value)} aria-label="Month" />
        </div>

        {loading ? (
          <p className="text-sm text-slate-500">Loading…</p>
        ) : items.length === 0 ? (
          <p className="text-sm text-slate-500">No {noun} entries for this month yet. Add your first one above.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="py-2 pr-4">Date</th>
                  <th className="py-2 pr-4">{categoryLabel}</th>
                  <th className="py-2 pr-4">Description</th>
                  <th className="py-2 pr-4">Method</th>
                  <th className="py-2 pr-4 text-right">Amount</th>
                  <th className="py-2" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((t) => (
                  <tr key={t.id}>
                    <td className="whitespace-nowrap py-2 pr-4">{t.transaction_date}</td>
                    <td className="py-2 pr-4 font-medium">{t.category}</td>
                    <td className="py-2 pr-4 text-slate-600">{t.description}</td>
                    <td className="py-2 pr-4 text-slate-600">{t.payment_method}</td>
                    <td className="py-2 pr-4 text-right tabular-nums">{inr(t.amount)}</td>
                    <td className="whitespace-nowrap py-2 text-right">
                      <button onClick={() => startEdit(t)} className="mr-3 text-brand-600 hover:underline">Edit</button>
                      <button onClick={() => remove(t)} className="text-rose-600 hover:underline">Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
