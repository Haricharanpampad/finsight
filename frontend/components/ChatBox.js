"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/services/api";

export const SUGGESTIONS = [
  "How is my business doing?",
  "How much did I spend this month?",
  "What was my profit last month?",
  "Why is my profit lower this month?",
  "Which expense is increasing the most?",
  "What can I do to increase my profit?",
  "If I reduce my monthly expenses by ₹5,000, what happens to my profit?",
  "What happens if I increase my price by 5%?",
];

const TOOL_LABELS = {
  get_total_revenue: "revenue", get_total_expenses: "expenses", get_profit: "profit", get_expenses_by_category: "expense categories",
  get_revenue_by_source: "revenue sources", compare_months: "month comparison", get_top_expenses: "top expenses",
  get_expense_growth: "expense growth", get_profit_margin: "profit margin", get_business_trends: "trends",
  forecast_revenue: "forecast", calculate_scenario: "what-if calculator", generate_business_recommendations: "recommendations",
};

/** The Ask FinSight chat. Numbers in answers come from the backend's analytics tools, never from the model. */
export default function ChatBox({ initialQuestion }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef(null);
  const sentInitial = useRef(false);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  async function send(text) {
    const question = (text ?? input).trim();
    if (!question || busy) return;
    const history = messages.filter((m) => !m.error).map((m) => ({ role: m.role, text: m.text })).slice(-10);
    setMessages((m) => [...m, { role: "user", text: question }]);
    setInput("");
    setBusy(true);
    try {
      const res = await api.chat(question, history);
      setMessages((m) => [...m, { role: "assistant", text: res.answer, tools: res.tools_used, mode: res.mode }]);
    } catch (err) {
      setMessages((m) => [...m, { role: "assistant", text: err.message, error: true }]);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (initialQuestion && !sentInitial.current) {
      sentInitial.current = true;
      send(initialQuestion);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialQuestion]);

  return (
    <div className="card flex h-[calc(100vh-14rem)] min-h-[420px] flex-col p-0">
      <div className="flex-1 space-y-4 overflow-y-auto p-5">
        {messages.length === 0 && (
          <div>
            <p className="text-lg font-semibold">Ask FinSight anything about your business</p>
            <p className="mt-1 text-sm text-slate-500">Answers are calculated from your own transactions. Try one of these:</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => send(s)} className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-left text-sm text-slate-700 hover:border-brand-500 hover:bg-brand-50">
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
            <div
              className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                m.role === "user" ? "bg-brand-600 text-white" : m.error ? "border border-rose-200 bg-rose-50 text-rose-800" : "bg-slate-100 text-slate-800"
              }`}
            >
              {m.text}
              {m.role === "assistant" && !m.error && m.tools?.length > 0 && (
                <p className="mt-2 border-t border-slate-200 pt-2 text-xs text-slate-500">
                  Numbers from: {[...new Set(m.tools)].map((t) => TOOL_LABELS[t] || t).join(", ")}
                  {m.mode === "gemini" ? " · explained by Gemini" : " · built-in analyst"}
                </p>
              )}
            </div>
          </div>
        ))}

        {busy && <div className="text-sm text-slate-500">FinSight is checking your numbers…</div>}
        <div ref={bottomRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
        className="flex gap-2 border-t border-slate-200 p-3"
      >
        <input className="input" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask FinSight anything…" maxLength={1000} />
        <button className="btn" disabled={busy || !input.trim()}>Send</button>
      </form>
    </div>
  );
}
