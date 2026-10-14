"""Analytics engine: every financial number in FinSight is computed here.

This module only needs pandas/numpy (no database, no web framework), so it is easy to
unit-test. The AI layer calls these methods through "tools" and only *explains* the
results - it never does the arithmetic itself.

Row format (one dict per transaction):
    {"type": "revenue" | "expense", "amount": 1200.0, "category": "Marketing", "date": date(...)}
"""
from __future__ import annotations

import calendar
import re
from datetime import date

import numpy as np
import pandas as pd

COLUMNS = ["type", "amount", "category", "date"]


# --------------------------------------------------------------------------- helpers
def inr(value: float, decimals: int = 0) -> str:
    """Format a number in Indian digit grouping: 125000 -> ₹1,25,000."""
    negative = value < 0
    s = f"{abs(round(float(value), decimals)):.{decimals}f}"
    whole, _, frac = s.partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts + [tail])
    out = "₹" + whole + (f".{frac}" if decimals else "")
    return "-" + out if negative else out


def pct_change(current: float, previous: float) -> float | None:
    """Percentage change, or None when there is no previous value to compare with."""
    if not previous:
        return None
    return round((current - previous) / previous * 100, 1)


def shift_month(ym: str, delta: int) -> str:
    year, month = map(int, ym.split("-"))
    idx = year * 12 + (month - 1) + delta
    return f"{idx // 12:04d}-{idx % 12 + 1:02d}"


def month_label(ym: str) -> str:
    year, month = map(int, ym.split("-"))
    return f"{calendar.month_name[month]} {year}"


_MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


# --------------------------------------------------------------------------- engine
class Analytics:
    def __init__(self, rows, today: date | None = None):
        df = rows.copy() if isinstance(rows, pd.DataFrame) else pd.DataFrame(list(rows))
        for col in COLUMNS:
            if col not in df.columns:
                df[col] = pd.Series(dtype="object")
        df = df[COLUMNS].copy()
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
        df["date"] = pd.to_datetime(df["date"])
        df["month"] = df["date"].dt.strftime("%Y-%m")
        self.df = df
        self.today = today or date.today()
        self.current_month = f"{self.today.year:04d}-{self.today.month:02d}"

    # ---- period handling
    def resolve_month(self, month: str | None = None) -> str:
        if month in (None, "", "this_month", "current", "current_month"):
            return self.current_month
        if month in ("last_month", "previous", "previous_month"):
            return shift_month(self.current_month, -1)
        if _MONTH_RE.match(month):
            return month
        raise ValueError(f"Unknown month '{month}'. Use 'this_month', 'last_month' or 'YYYY-MM'.")

    def _upto(self, month: str) -> int | None:
        """For the in-progress month, comparisons stop at today's day-of-month (like-for-like)."""
        return self.today.day if month == self.current_month else None

    def _slice(self, month: str, upto_day: int | None = None) -> pd.DataFrame:
        d = self.df[self.df["month"] == month]
        if upto_day:
            d = d[d["date"].dt.day <= upto_day]
        return d

    def _total(self, kind: str, month: str, category: str | None = None, upto_day: int | None = None) -> float:
        d = self._slice(month, upto_day)
        d = d[d["type"] == kind]
        if category:
            d = d[d["category"].str.lower() == category.lower()]
        return round(float(d["amount"].sum()), 2)

    def has_data(self, month: str) -> bool:
        return not self._slice(month).empty

    def categories(self, kind: str = "expense") -> list[str]:
        return sorted(self.df[self.df["type"] == kind]["category"].dropna().unique().tolist())

    # ---- basic metrics
    def summary(self, month: str | None = None, upto_day: int | None = None) -> dict:
        m = self.resolve_month(month)
        revenue = self._total("revenue", m, upto_day=upto_day)
        expenses = self._total("expense", m, upto_day=upto_day)
        profit = round(revenue - expenses, 2)  # Profit = Revenue - Expenses
        margin = round(profit / revenue * 100, 1) if revenue else None  # (Profit / Revenue) x 100
        return {"month": m, "revenue": revenue, "expenses": expenses, "profit": profit, "profit_margin_pct": margin}

    def category_total(self, category: str, month: str | None = None) -> dict:
        m = self.resolve_month(month)
        cur = self._total("expense", m, category)
        prev = self._total("expense", shift_month(m, -1), category, upto_day=self._upto(m))
        return {"category": category, "month": m, "amount": cur, "previous": prev,
                "change": round(cur - prev, 2), "change_pct": pct_change(cur, prev)}

    def by_category(self, kind: str = "expense", month: str | None = None) -> list[dict]:
        m = self.resolve_month(month)
        d = self._slice(m)
        d = d[d["type"] == kind]
        g = d.groupby("category")["amount"].sum().sort_values(ascending=False)
        total = float(g.sum())
        return [
            {"category": c, "amount": round(float(a), 2), "share_pct": round(float(a) / total * 100, 1) if total else 0.0}
            for c, a in g.items()
        ]

    def top_expenses(self, month: str | None = None, n: int = 5) -> list[dict]:
        return self.by_category("expense", month)[: max(1, int(n))]

    # ---- comparison / growth
    def compare_months(self, month: str | None = None, previous: str | None = None) -> dict:
        cur_m = self.resolve_month(month)
        prev_m = self.resolve_month(previous) if previous else shift_month(cur_m, -1)
        upto = self._upto(cur_m) if prev_m == shift_month(cur_m, -1) else None
        cur = self.summary(cur_m)
        prev = self.summary(prev_m, upto_day=upto)
        change = {k: round(cur[k] - prev[k], 2) for k in ("revenue", "expenses", "profit")}
        change_pct = {k: pct_change(cur[k], prev[k]) for k in ("revenue", "expenses", "profit")}
        if cur["profit"] <= 0 or prev["profit"] <= 0:
            change_pct["profit"] = None  # a % change is meaningless when profit is zero or negative
        return {
            "current_month": cur_m,
            "previous_month": prev_m,
            "like_for_like": upto is not None,
            "through_day": upto,
            "current": cur,
            "previous": prev,
            "change": change,
            "change_pct": change_pct,
        }

    def category_growth(self, month: str | None = None, previous: str | None = None, kind: str = "expense") -> list[dict]:
        cur_m = self.resolve_month(month)
        prev_m = self.resolve_month(previous) if previous else shift_month(cur_m, -1)
        upto = self._upto(cur_m) if prev_m == shift_month(cur_m, -1) else None
        cur = self._slice(cur_m)
        cur = cur[cur["type"] == kind].groupby("category")["amount"].sum()
        prev = self._slice(prev_m, upto)
        prev = prev[prev["type"] == kind].groupby("category")["amount"].sum()
        rows = []
        for cat in sorted(set(cur.index) | set(prev.index)):
            c, p = float(cur.get(cat, 0.0)), float(prev.get(cat, 0.0))
            rows.append({"category": cat, "current": round(c, 2), "previous": round(p, 2),
                         "change": round(c - p, 2), "change_pct": pct_change(c, p)})
        rows.sort(key=lambda r: r["change"], reverse=True)
        return rows

    def monthly_trend(self, months: int = 6) -> list[dict]:
        months = max(1, min(int(months), 24))
        out = []
        for i in range(months - 1, -1, -1):
            m = shift_month(self.current_month, -i)
            s = self.summary(m)
            s["label"] = calendar.month_abbr[int(m[5:])]
            s["partial"] = m == self.current_month
            out.append(s)
        return out

    # ---- forecasting
    def forecast_revenue(self, months_ahead: int = 1, history: int = 6) -> dict:
        """Simple linear-trend forecast over completed months. An estimate, not a guarantee."""
        months_ahead = max(1, min(int(months_ahead), 6))
        hist = [self.summary(shift_month(self.current_month, -i)) for i in range(history, 0, -1)]
        hist = [h for h in hist if h["revenue"] > 0]
        if len(hist) < 3:
            return {"available": False, "reason": "Need at least 3 completed months of revenue to forecast."}
        y = np.array([h["revenue"] for h in hist])
        x = np.arange(len(y))
        slope, intercept = np.polyfit(x, y, 1)
        # The target month is `months_ahead` after the current month; history ends the month before it.
        target_x = len(y) - 1 + months_ahead + 1
        predicted = max(0.0, float(slope * target_x + intercept))
        resid = y - (slope * x + intercept)
        spread = float(np.std(resid, ddof=1)) if len(y) > 2 else 0.0
        spread = max(spread, predicted * 0.03)
        return {
            "available": True,
            "target_month": shift_month(self.current_month, months_ahead),
            "method": f"linear trend over the last {len(y)} completed months",
            "estimate": round(predicted, 2),
            "low": round(max(0.0, predicted - spread), 2),
            "high": round(predicted + spread, 2),
            "avg_monthly_growth": round(float(slope), 2),
            "is_forecast": True,
            "note": "This is a statistical estimate, not a guaranteed result.",
        }

    # ---- what-if analysis
    def baseline_month(self) -> str:
        last = shift_month(self.current_month, -1)
        return last if self.has_data(last) else self.current_month

    def scenario(
        self,
        price_change_pct: float = 0.0,
        sales_change_pct: float = 0.0,
        expense_change_amount: float = 0.0,
        expense_change_pct: float = 0.0,
        category: str | None = None,
        month: str | None = None,
    ) -> dict:
        m = self.resolve_month(month) if month else self.baseline_month()
        base = self.summary(m)
        revenue_factor = (1 + price_change_pct / 100) * (1 + sales_change_pct / 100)
        projected_revenue = base["revenue"] * revenue_factor

        target_base = self._total("expense", m, category) if category else base["expenses"]
        target_new = max(0.0, target_base * (1 + expense_change_pct / 100) + expense_change_amount)
        projected_expenses = base["expenses"] - target_base + target_new

        profit_new = projected_revenue - projected_expenses
        assumptions = ["Based on " + month_label(m) + " figures."]
        if price_change_pct or sales_change_pct:
            assumptions.append("Expenses stay the same when prices/sales change (no extra stock or staff cost).")
        if price_change_pct and not sales_change_pct:
            assumptions.append("Sales volume stays constant after the price change.")
        return {
            "basis_month": m,
            "baseline": base,
            "projected": {
                "revenue": round(projected_revenue, 2),
                "expenses": round(projected_expenses, 2),
                "profit": round(profit_new, 2),
                "profit_margin_pct": round(profit_new / projected_revenue * 100, 1) if projected_revenue else None,
            },
            "profit_change": round(profit_new - base["profit"], 2),
            "inputs": {
                "price_change_pct": price_change_pct, "sales_change_pct": sales_change_pct,
                "expense_change_amount": expense_change_amount, "expense_change_pct": expense_change_pct,
                "category": category,
            },
            "assumptions": assumptions,
            "is_projection": True,
        }

    # ---- recommendations
    def recommendations(self, month: str | None = None) -> list[dict]:
        m = self.resolve_month(month)
        # While the current month is only days old, judge on the last full month: early-month numbers
        # are noisy (rent is paid on day 1, big orders land later) and would give shaky advice.
        ref = shift_month(m, -1) if m == self.current_month and self.has_data(shift_month(m, -1)) else m
        cmp = self.compare_months(ref)
        growth = self.category_growth(ref)
        rev_pct, exp_pct = cmp["change_pct"]["revenue"], cmp["change_pct"]["expenses"]
        when = month_label(ref)
        recs: list[dict] = []

        if growth and growth[0]["change"] > 0 and exp_pct is not None and exp_pct > (rev_pct or 0) + 5:
            top = growth[0]
            recs.append({
                "severity": "warning",
                "title": f"{top['category']} is driving up your costs",
                "detail": (
                    f"In {when}, expenses grew {exp_pct}% while revenue "
                    + ("was flat" if not rev_pct else f"{'grew' if rev_pct > 0 else 'fell'} {abs(rev_pct)}%")
                    + ". "
                    f"{top['category']} is the biggest contributor"
                    + (f" (up {top['change_pct']}%)" if top["change_pct"] is not None else "")
                    + f". Bringing it back near {month_label(cmp['previous_month'])}'s level could improve profit by roughly {inr(top['change'])}."
                ),
                "potential_saving": top["change"],
                "steps": [
                    f"Review every {top['category']} entry this month and flag one-off or unusual spends.",
                    f"Ask your main {top['category']} suppliers/vendors for fresh quotes or bulk discounts.",
                    f"Set a monthly {top['category']} budget near {inr(top['previous'])} and check it weekly.",
                ],
            })

        for g in growth[1:]:
            if g["change_pct"] is not None and g["change_pct"] >= 15 and g["change"] >= 1000:
                recs.append({
                    "severity": "watch",
                    "title": f"{g['category']} is rising ({g['change_pct']}%)",
                    "detail": f"{g['category']} went from {inr(g['previous'])} to {inr(g['current'])} in {when} - worth keeping an eye on.",
                    "potential_saving": g["change"],
                    "steps": [f"Check whether the {g['category']} increase is a one-off or a new regular cost."],
                })
                if len(recs) >= 3:
                    break

        ref_summary = self.summary(ref)
        margin = ref_summary["profit_margin_pct"]
        if margin is not None and margin < 15:
            recs.append({
                "severity": "warning",
                "title": "Profit margin is thin",
                "detail": f"Your margin in {month_label(ref)} was {margin}%. A 5% price increase (if customers stay) would add about {inr(ref_summary['revenue'] * 0.05)} to profit.",
                "potential_saving": round(ref_summary["revenue"] * 0.05, 2),
                "steps": ["Try the what-if tool: 'What happens if I increase my price by 5%?'"],
            })

        expense_cats = self.by_category("expense", ref)
        if expense_cats and expense_cats[0]["share_pct"] >= 40 and len(expense_cats) > 1:
            c = expense_cats[0]
            recs.append({
                "severity": "info",
                "title": f"{c['category']} is {c['share_pct']}% of your spending",
                "detail": f"That's the share in {month_label(ref)}. A large share in one category means small savings there matter most.",
                "potential_saving": round(c["amount"] * 0.05, 2),
                "steps": [f"A 5% saving on {c['category']} would be about {inr(c['amount'] * 0.05)} a month."],
            })

        sources = self.by_category("revenue", ref)
        if sources and sources[0]["share_pct"] >= 60 and len(sources) > 1:
            recs.append({
                "severity": "info",
                "title": f"{sources[0]['category']} brings {sources[0]['share_pct']}% of revenue",
                "detail": "Depending on one source is risky - consider growing your smaller revenue sources.",
                "potential_saving": 0.0,
                "steps": ["Pick the second-largest source and plan one action to grow it this month."],
            })

        if not recs:
            recs.append({
                "severity": "good",
                "title": "Costs look under control",
                "detail": "No expense category is growing unusually fast compared with revenue.",
                "potential_saving": 0.0,
                "steps": ["Keep logging every transaction so FinSight can spot changes early."],
            })
        return recs
