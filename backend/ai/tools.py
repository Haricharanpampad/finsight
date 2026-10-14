"""Tools (functions) the AI assistant can call.

Each tool is a thin wrapper around the Analytics engine. The LLM chooses *which* tool to
call and with *what arguments*; the numbers always come from the engine, never from the model.
"""
from __future__ import annotations

from typing import Any, Callable

from services.analytics_service import Analytics, inr

MONTH_PARAM = {
    "type": "string",
    "description": "Month to look at: 'this_month', 'last_month', or 'YYYY-MM'. Defaults to this_month.",
}

TOOL_SPECS: list[dict] = [
    {"name": "get_total_revenue", "description": "Total revenue for a month.",
     "parameters": {"type": "object", "properties": {"month": MONTH_PARAM}}},
    {"name": "get_total_expenses",
     "description": "Total expenses for a month, optionally for one category (e.g. Marketing).",
     "parameters": {"type": "object", "properties": {
         "month": MONTH_PARAM, "category": {"type": "string", "description": "Expense category name, optional."}}}},
    {"name": "get_profit", "description": "Revenue, expenses, profit and profit margin for a month.",
     "parameters": {"type": "object", "properties": {"month": MONTH_PARAM}}},
    {"name": "get_expenses_by_category", "description": "Expenses grouped by category with each share of spending.",
     "parameters": {"type": "object", "properties": {"month": MONTH_PARAM}}},
    {"name": "get_revenue_by_source", "description": "Revenue grouped by source.",
     "parameters": {"type": "object", "properties": {"month": MONTH_PARAM}}},
    {"name": "compare_months",
     "description": "Compare a month with the previous month: revenue, expenses, profit and % changes. "
                    "Use this to explain why profit rose or fell. For the current month the comparison is like-for-like (same days).",
     "parameters": {"type": "object", "properties": {
         "month": MONTH_PARAM, "previous_month": {"type": "string", "description": "Optional month to compare with."}}}},
    {"name": "get_top_expenses", "description": "Largest expense categories for a month.",
     "parameters": {"type": "object", "properties": {
         "month": MONTH_PARAM, "n": {"type": "integer", "description": "How many categories (default 5)."}}}},
    {"name": "get_expense_growth",
     "description": "Per-category expense change versus the previous month, biggest increase first. "
                    "Use to find which expense is increasing the most.",
     "parameters": {"type": "object", "properties": {"month": MONTH_PARAM}}},
    {"name": "get_profit_margin", "description": "Profit margin percentage for a month.",
     "parameters": {"type": "object", "properties": {"month": MONTH_PARAM}}},
    {"name": "get_business_trends", "description": "Monthly revenue, expenses and profit for the last N months.",
     "parameters": {"type": "object", "properties": {
         "months": {"type": "integer", "description": "Number of months (default 6)."}}}},
    {"name": "forecast_revenue",
     "description": "Estimate revenue for an upcoming month using the historical trend. This is a forecast, not a guarantee.",
     "parameters": {"type": "object", "properties": {
         "months_ahead": {"type": "integer", "description": "1 = next month after this one (default 1)."}}}},
    {"name": "calculate_scenario",
     "description": "What-if analysis. Provide any of: price_change_pct (e.g. 5 for +5%), sales_change_pct, "
                    "expense_change_amount in rupees (negative to reduce), expense_change_pct, and optionally a category "
                    "to apply the expense change to. Returns the projected profit.",
     "parameters": {"type": "object", "properties": {
         "price_change_pct": {"type": "number"}, "sales_change_pct": {"type": "number"},
         "expense_change_amount": {"type": "number"}, "expense_change_pct": {"type": "number"},
         "category": {"type": "string"}}}},
    {"name": "generate_business_recommendations",
     "description": "Specific, number-backed suggestions to improve profit, with concrete steps.",
     "parameters": {"type": "object", "properties": {"month": MONTH_PARAM}}},
]

# Keys whose numeric values are rupee amounts; we add a formatted "<key>_inr" copy so the model
# can quote the exact figure instead of re-formatting numbers itself.
_MONEY_KEYS = {
    "revenue", "expenses", "profit", "amount", "previous", "current", "change", "estimate", "low", "high",
    "potential_saving", "profit_change", "avg_monthly_growth", "expense_change_amount",
}


def _with_inr(obj: Any) -> Any:
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            out[k] = _with_inr(v)
            if k in _MONEY_KEYS and isinstance(v, (int, float)) and not isinstance(v, bool):
                out[f"{k}_inr"] = inr(v)
        return out
    if isinstance(obj, list):
        return [_with_inr(i) for i in obj]
    return obj


def _tools(a: Analytics) -> dict[str, Callable[..., Any]]:
    return {
        "get_total_revenue": lambda month=None: {"month": a.resolve_month(month), "revenue": a.summary(month)["revenue"]},
        "get_total_expenses": lambda month=None, category=None: (
            a.category_total(category, month) if category
            else {"month": a.resolve_month(month), "expenses": a.summary(month)["expenses"]}
        ),
        "get_profit": lambda month=None: a.summary(month),
        "get_expenses_by_category": lambda month=None: {"month": a.resolve_month(month), "categories": a.by_category("expense", month)},
        "get_revenue_by_source": lambda month=None: {"month": a.resolve_month(month), "sources": a.by_category("revenue", month)},
        "compare_months": lambda month=None, previous_month=None: a.compare_months(month, previous_month),
        "get_top_expenses": lambda month=None, n=5: {"month": a.resolve_month(month), "top": a.top_expenses(month, n)},
        "get_expense_growth": lambda month=None: {"month": a.resolve_month(month), "categories": a.category_growth(month)},
        "get_profit_margin": lambda month=None: {k: a.summary(month)[k] for k in ("month", "profit_margin_pct")},
        "get_business_trends": lambda months=6: {"trend": a.monthly_trend(months)},
        "forecast_revenue": lambda months_ahead=1: a.forecast_revenue(months_ahead),
        "calculate_scenario": lambda **kw: a.scenario(**{k: v for k, v in kw.items() if v is not None}),
        "generate_business_recommendations": lambda month=None: {"recommendations": a.recommendations(month)},
    }


def run_tool(analytics: Analytics, name: str, args: dict | None = None) -> dict:
    """Execute a tool by name. Unknown tools / bad arguments return an error dict instead of raising."""
    fn = _tools(analytics).get(name)
    if fn is None:
        return {"error": f"Unknown tool '{name}'."}
    try:
        return _with_inr(fn(**(args or {})))
    except (TypeError, ValueError) as exc:
        return {"error": str(exc)}
