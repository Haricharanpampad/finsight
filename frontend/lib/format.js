const inrFormatter = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });

/** 125000 -> ₹1,25,000 */
export const inr = (n) => (n === null || n === undefined ? "—" : inrFormatter.format(n));

/** Short form for chart axes: 125000 -> ₹1.3L */
export function compactInr(n) {
  const a = Math.abs(n);
  const sign = n < 0 ? "-" : "";
  if (a >= 1e7) return `${sign}₹${(a / 1e7).toFixed(1)}Cr`;
  if (a >= 1e5) return `${sign}₹${(a / 1e5).toFixed(1)}L`;
  if (a >= 1e3) return `${sign}₹${(a / 1e3).toFixed(0)}K`;
  return `${sign}₹${a}`;
}

export const pct = (n) => (n === null || n === undefined ? "—" : `${n > 0 ? "+" : ""}${n}%`);

export function monthLabel(ym) {
  if (!ym) return "";
  const [y, m] = ym.split("-");
  return new Date(Number(y), Number(m) - 1, 1).toLocaleString("en-IN", { month: "long", year: "numeric" });
}

/** Today as YYYY-MM-DD in the browser's local time. */
export function todayISO() {
  const d = new Date();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${mm}-${dd}`;
}

export const thisMonth = () => todayISO().slice(0, 7);
