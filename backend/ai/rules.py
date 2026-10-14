"""Built-in rule-based assistant.

Works with no API key: it detects the intent of the question, calls the same tools the LLM
would call, and writes the answer from the tool results. This keeps FinSight usable offline
and acts as the fallback when the Gemini API is unavailable.
"""
from __future__ import annotations

import calendar
import re

from ai.tools import run_tool
from services.analytics_service import Analytics, inr, month_label, shift_month

_NEGATIVE_VERBS = {"reduce", "cut", "lower", "decrease", "drop", "trim", "fall", "falls", "drops", "decreases"}
_MONTH_NAMES = {n.lower(): i for i, n in enumerate(calendar.month_name) if n}
_NUM = r"(\d[\d,]*(?:\.\d+)?)"
_CUR = r"(?:rs\.?\s*|₹\s*|inr\s*)?"
_UNIT = r"\s*(%|percent|k|l|lakh|lakhs)?"

HELP = (
    "I can answer questions about your numbers. Try: \"How much did I spend this month?\", "
    "\"What was my profit last month?\", \"Why is my profit lower this month?\", "
    "\"Which expense is increasing the most?\", \"What can I do to increase my profit?\", or "
    "\"If I reduce my monthly expenses by ₹5,000, what happens to my profit?\""
)


def _to_number(raw: str, unit: str | None) -> tuple[float, bool]:
    """Return (value, is_percent)."""
    value = float(raw.replace(",", ""))
    unit = (unit or "").lower()
    if unit in ("%", "percent"):
        return value, True
    if unit == "k":
        return value * 1_000, False
    if unit in ("l", "lakh", "lakhs"):
        return value * 100_000, False
    return value, False


def parse_scenario(text: str, categories: list[str]) -> dict | None:
    """Turn 'what if I reduce marketing by ₹2,000' into calculate_scenario arguments."""
    t = text.lower()
    verb_first = re.search(
        r"\b(increase|raise|hike|grow|boost|reduce|cut|lower|decrease|drop|trim)\w*\s+(?:my\s+|the\s+|our\s+)?(?:monthly\s+)?"
        r"([a-z ]+?)\s+by\s+" + _CUR + _NUM + _UNIT, t)
    noun_first = re.search(
        r"\b(sales|revenue|prices?)\s+(?:increases?|grow|grows|rise|rises|go(?:es)? up|drops?|falls?|decreases?|go(?:es)? down)\s+by\s+"
        + _CUR + _NUM + _UNIT, t)

    if verb_first:
        verb, noun, raw, unit = verb_first.groups()
        sign = -1 if verb in _NEGATIVE_VERBS else 1
    elif noun_first:
        noun, raw, unit = noun_first.groups()
        sign = -1 if re.search(r"drop|fall|decrease|go(?:es)? down", noun_first.group(0)) else 1
    else:
        return None

    value, is_pct = _to_number(raw, unit)
    value *= sign
    noun = noun.strip()

    if "price" in noun:
        return {"price_change_pct": value}
    if any(w in noun for w in ("sales", "revenue", "customer", "volume", "income")):
        return {"sales_change_pct": value}

    category = next((c for c in sorted(categories, key=len, reverse=True) if c.lower() in noun), None)
    is_expense_word = any(w in noun for w in ("expense", "spend", "cost"))
    if not category and not is_expense_word:
        return None
    args: dict = {"expense_change_pct": value} if is_pct else {"expense_change_amount": value}
    if category:
        args["category"] = category
    return args


def parse_month(text: str, a: Analytics) -> str | None:
    t = text.lower()
    if re.search(r"last month|previous month", t):
        return "last_month"
    if "this month" in t or "current month" in t:
        return "this_month"
    m = re.search(r"\b(?:in|for|of|during)\s+(" + "|".join(_MONTH_NAMES) + r")\b(?:\s+(\d{4}))?", t)
    if m:
        month_no = _MONTH_NAMES[m.group(1)]
        year = int(m.group(2)) if m.group(2) else a.today.year
        ym = f"{year:04d}-{month_no:02d}"
        if not m.group(2) and ym > a.current_month:
            ym = f"{year - 1:04d}-{month_no:02d}"
        return ym
    return None


class RuleAssistant:
    def __init__(self, analytics: Analytics):
        self.a = analytics
        self.tools_used: list[str] = []

    # --- plumbing
    def _call(self, name: str, **args) -> dict:
        self.tools_used.append(name)
        return run_tool(self.a, name, {k: v for k, v in args.items() if v is not None})

    def _period(self, month: str | None) -> str:
        m = self.a.resolve_month(month)
        return "this month so far" if m == self.a.current_month else f"in {month_label(m)}"

    @staticmethod
    def _vs(cmp: dict) -> str:
        return "the same days last month" if cmp["like_for_like"] else month_label(cmp["previous_month"])

    @staticmethod
    def _dir(x: float) -> str:
        return "higher" if x >= 0 else "lower"

    # --- entry point
    def respond(self, message: str) -> tuple[str, list[str]]:
        t = message.lower().strip()
        a = self.a
        month = parse_month(t, a)
        cats = a.categories("expense")

        scenario = parse_scenario(message, cats)
        if scenario:
            return self._scenario(scenario), self.tools_used

        if re.search(r"\bforecast|predict|next month|projection|expected (revenue|sales)", t):
            return self._forecast(), self.tools_used
        if re.search(r"how can i|what can i do|improve|recommend|suggest|advice|opportunit|show me how|action plan|save money|"
                     r"(increase|boost|grow) (my )?profit|(reduce|cut|lower) (my )?(costs?|expenses?|spending)", t):
            return self._recommend(month, steps=bool(re.search(r"show me how|action plan|steps", t))), self.tools_used

        mentioned_cat = next((c for c in sorted(cats, key=len, reverse=True) if c.lower() in t), None)

        if not a.has_data(a.resolve_month(month)) and not re.search(r"trend|history|forecast", t):
            return (f"I don't see any transactions {self._period(month)} yet. "
                    "Add some revenue and expenses and I'll be able to answer."), self.tools_used

        if re.search(r"why.*(profit|earning|margin|money)|profit.*(lower|higher|fall|fell|drop|dropped|decreas|increas|down|up\b|change)", t):
            return self._why_profit(month), self.tools_used
        if re.search(r"(which|what).*(expense|cost|spend).*(increas|grow|rising|up|most)|increasing the most|biggest increase|fastest", t):
            return self._growth(month), self.tools_used
        if mentioned_cat and re.search(r"spend|spent|expense|cost|paid|pay", t):
            return self._category(mentioned_cat, month), self.tools_used
        if re.search(r"top expense|biggest expense|largest|where.*(spend|money go)|breakdown|by category", t):
            return self._top_expenses(month), self.tools_used
        if re.search(r"revenue (by|sources?)|sources? of (revenue|income)|where.*(revenue|income|sales) come", t):
            return self._sources(month), self.tools_used
        if "margin" in t:
            return self._profit(month, margin_focus=True), self.tools_used
        if re.search(r"trend|history|over time|last \d+ months|monthly", t):
            return self._trend(), self.tools_used
        if re.search(r"how.*(business|doing|going)|overview|summary|status|snapshot", t):
            return self._profit(month, overview=True), self.tools_used
        if re.search(r"profit|loss|earn|made", t):
            return self._profit(month), self.tools_used
        if re.search(r"revenue|sales|income|sold|turnover", t):
            return self._revenue(month), self.tools_used
        if re.search(r"spend|spent|expense|cost", t):
            return self._spend(month), self.tools_used
        return HELP, self.tools_used

    # --- answers
    def _revenue(self, month):
        r = self._call("get_total_revenue", month=month)
        return f"Your revenue {self._period(month)} is {inr(r['revenue'])}."

    def _spend(self, month):
        r = self._call("get_total_expenses", month=month)
        cmp = self._call("compare_months", month=month)
        pct = cmp["change_pct"]["expenses"]
        extra = ""
        if pct is not None:
            extra = f" That's {abs(pct)}% {'more' if pct >= 0 else 'less'} than {self._vs(cmp)}."
        top = self._call("get_top_expenses", month=month, n=1)["top"]
        if top:
            extra += f" Your biggest category is {top[0]['category']} at {inr(top[0]['amount'])}."
        return f"You spent {inr(r['expenses'])} {self._period(month)}.{extra}"

    def _category(self, category, month):
        r = self._call("get_total_expenses", month=month, category=category)
        text = f"You spent {inr(r['amount'])} on {category} {self._period(month)}"
        if r["previous"]:
            diff = r["change"]
            text += f", which is {inr(abs(diff))} {'more' if diff >= 0 else 'less'} than the same period last month"
        return text + "."

    def _profit(self, month, margin_focus=False, overview=False):
        p = self._call("get_profit", month=month)
        cmp = self._call("compare_months", month=month)
        text = ""
        if margin_focus:
            if p["profit_margin_pct"] is None:
                return f"There is no revenue {self._period(month)}, so there is no profit margin yet."
            text = f"Your profit margin {self._period(month)} is {p['profit_margin_pct']}%. "
        text += (f"Your profit {self._period(month)} is {inr(p['profit'])} "
                 f"(revenue {inr(p['revenue'])} minus expenses {inr(p['expenses'])}")
        if p["profit_margin_pct"] is not None and not margin_focus:
            text += f", a margin of {p['profit_margin_pct']}%"
        text += ")."
        if cmp["previous"]["revenue"] or cmp["previous"]["expenses"]:
            d = cmp["change"]["profit"]
            text += f" That's {inr(abs(d))} {self._dir(d)} than {self._vs(cmp)}."
        if overview:
            text += " Ask me \"why did my profit change?\" or \"what can I do to increase my profit?\" to dig in."
        return text

    def _why_profit(self, month):
        cmp = self._call("compare_months", month=month)
        growth = self._call("get_expense_growth", month=month)["categories"]
        cur, prev, ch, pc = cmp["current"], cmp["previous"], cmp["change"], cmp["change_pct"]
        vs = self._vs(cmp)
        if not (prev["revenue"] or prev["expenses"]):
            return f"I don't have data for {vs} to compare with, so I can't explain the change yet."
        d = ch["profit"]
        pct = f" ({abs(pc['profit'])}%)" if pc["profit"] is not None else ""
        parts = [f"Your profit {self._period(month)} is {inr(cur['profit'])}, {inr(abs(d))}{pct} {self._dir(d)} than {vs}."]
        rev_pct, exp_pct = pc["revenue"], pc["expenses"]
        def move(x: float, p: float | None) -> str:
            word = "up" if x >= 0 else "down"
            return f"{word} {inr(abs(x))}" + (f" ({abs(p)}%)" if p is not None else "")

        parts.append(f"Revenue is {move(ch['revenue'], rev_pct)} and expenses are {move(ch['expenses'], exp_pct)}.")
        if d < 0 and growth and growth[0]["change"] > 0:
            g = growth[0]
            tail = f" (up {g['change_pct']}%)" if g["change_pct"] is not None else ""
            parts.append(f"The biggest driver is {g['category']}, which rose by {inr(g['change'])}{tail}.")
        elif d >= 0 and growth and growth[-1]["change"] < 0:
            g = growth[-1]
            parts.append(f"{g['category']} helped most - it fell by {inr(abs(g['change']))}.")
        if d < 0:
            parts.append("Ask \"what can I do to increase my profit?\" for specific steps.")
        return " ".join(parts)

    def _growth(self, month):
        growth = self._call("get_expense_growth", month=month)["categories"]
        rising = [g for g in growth if g["change"] > 0][:3]
        if not rising:
            return "None of your expense categories has increased compared with the same period last month."
        lines = [f"{g['category']} (+{inr(g['change'])}" + (f", +{g['change_pct']}%" if g["change_pct"] is not None else "") + ")"
                 for g in rising]
        return (f"{rising[0]['category']} is increasing the most: it is up {inr(rising[0]['change'])} compared with the same period last month. "
                "Biggest increases: " + "; ".join(lines) + ".")

    def _top_expenses(self, month):
        top = self._call("get_top_expenses", month=month, n=5)["top"]
        lines = [f"{i}. {t['category']} - {inr(t['amount'])} ({t['share_pct']}%)" for i, t in enumerate(top, 1)]
        return f"Your biggest expenses {self._period(month)}:\n" + "\n".join(lines)

    def _sources(self, month):
        src = self._call("get_revenue_by_source", month=month)["sources"]
        lines = [f"{i}. {s['category']} - {inr(s['amount'])} ({s['share_pct']}%)" for i, s in enumerate(src, 1)]
        return f"Where your revenue came from {self._period(month)}:\n" + "\n".join(lines)

    def _trend(self):
        rows = self._call("get_business_trends", months=6)["trend"]
        lines = [f"{r['label']}: revenue {inr(r['revenue'])}, expenses {inr(r['expenses'])}, profit {inr(r['profit'])}"
                 + (" (month in progress)" if r["partial"] else "") for r in rows]
        return "Your last 6 months:\n" + "\n".join(lines)

    def _forecast(self):
        f = self._call("forecast_revenue", months_ahead=1)
        if not f.get("available"):
            return f["reason"]
        return (f"Forecast: FinSight estimates revenue for {month_label(f['target_month'])} at about {inr(f['estimate'])} "
                f"(likely range {inr(f['low'])} to {inr(f['high'])}), based on a {f['method']}. "
                "This is an estimate, not a guaranteed result.")

    def _recommend(self, month, steps=False):
        recs = self._call("generate_business_recommendations", month=month)["recommendations"]
        out = []
        for r in recs:
            block = f"- {r['title']}: {r['detail']}"
            if steps and r.get("steps"):
                block += "\n" + "\n".join(f"    {i}. {s}" for i, s in enumerate(r["steps"], 1))
            out.append(block)
        text = "Here is what the numbers suggest:\n" + "\n".join(out)
        if not steps:
            text += "\n\nSay \"show me how\" and I'll give you a step-by-step plan."
        return text

    def _scenario(self, args):
        r = self._call("calculate_scenario", **args)
        if "error" in r:
            return r["error"]
        i = r["inputs"]
        bits = []
        if i["price_change_pct"]:
            bits.append(f"{'raise' if i['price_change_pct'] > 0 else 'lower'} your prices by {abs(i['price_change_pct']):g}%")
        if i["sales_change_pct"]:
            bits.append(f"{'grow' if i['sales_change_pct'] > 0 else 'lose'} {abs(i['sales_change_pct']):g}% of sales")
        what = "total expenses" if not i["category"] else f"{i['category']} spending"
        if i["expense_change_amount"]:
            bits.append(f"{'increase' if i['expense_change_amount'] > 0 else 'cut'} {what} by {inr(abs(i['expense_change_amount']))}")
        if i["expense_change_pct"]:
            bits.append(f"{'increase' if i['expense_change_pct'] > 0 else 'cut'} {what} by {abs(i['expense_change_pct']):g}%")
        d = r["profit_change"]
        return (f"If you {' and '.join(bits)}, your monthly profit would go from {inr(r['baseline']['profit'])} to "
                f"{inr(r['projected']['profit'])} ({'+' if d >= 0 else '-'}{inr(abs(d))}). "
                f"This is a projection. {' '.join(r['assumptions'])}")
