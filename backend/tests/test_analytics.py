"""Tests for the analytics engine and rule-based assistant (no database or web framework needed).

Run with:  pytest            (or)   python tests/test_analytics.py
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ai.rules import RuleAssistant, parse_scenario  # noqa: E402
from ai.tools import run_tool  # noqa: E402
from demo_data import generate_demo_rows  # noqa: E402
from services.analytics_service import Analytics, inr, pct_change, shift_month  # noqa: E402

TODAY = date(2026, 10, 7)


def make():
    return Analytics(generate_demo_rows(TODAY), today=TODAY)


def test_inr_indian_grouping():
    assert inr(125000) == "₹1,25,000"
    assert inr(47000) == "₹47,000"
    assert inr(1234567) == "₹12,34,567"
    assert inr(-8000) == "-₹8,000"
    assert inr(0) == "₹0"


def test_formulas_on_known_numbers():
    rows = [
        {"type": "revenue", "amount": 120000, "category": "Sales", "date": date(2026, 9, 5)},
        {"type": "expense", "amount": 30000, "category": "Inventory", "date": date(2026, 9, 6)},
        {"type": "expense", "amount": 8000, "category": "Marketing", "date": date(2026, 9, 7)},
        {"type": "revenue", "amount": 125000, "category": "Sales", "date": date(2026, 10, 2)},
        {"type": "expense", "amount": 38000, "category": "Inventory", "date": date(2026, 10, 3)},
    ]
    a = Analytics(rows, today=date(2026, 10, 7))
    sep = a.summary("2026-09")
    assert sep["profit"] == 82000 and sep["profit_margin_pct"] == round(82000 / 120000 * 100, 1)
    cmp = a.compare_months("this_month")
    assert cmp["like_for_like"] and cmp["through_day"] == 7
    assert cmp["change_pct"]["revenue"] == pct_change(125000, 120000)
    inv = [g for g in a.category_growth() if g["category"] == "Inventory"][0]
    assert inv["change"] == 8000 and inv["change_pct"] == 26.7


def test_month_to_date_comparison_is_like_for_like():
    a = Analytics([
        {"type": "expense", "amount": 100, "category": "X", "date": date(2026, 9, 3)},
        {"type": "expense", "amount": 900, "category": "X", "date": date(2026, 9, 25)},  # after day 7: excluded
        {"type": "expense", "amount": 100, "category": "X", "date": date(2026, 10, 3)},
    ], today=date(2026, 10, 7))
    assert a.compare_months()["previous"]["expenses"] == 100
    assert a.compare_months()["change_pct"]["expenses"] == 0.0


def test_scenario_math():
    a = make()
    base = a.summary(a.baseline_month())
    s = a.scenario(expense_change_amount=-5000)
    assert s["profit_change"] == 5000
    assert s["projected"]["profit"] == round(base["profit"] + 5000, 2)
    p = a.scenario(price_change_pct=5)
    assert abs(p["profit_change"] - base["revenue"] * 0.05) < 0.01
    c = a.scenario(expense_change_amount=-2000, category="Marketing")
    assert c["profit_change"] == 2000


def test_forecast_needs_history_and_is_labelled():
    assert make().forecast_revenue()["available"]
    assert make().forecast_revenue()["is_forecast"]
    empty = Analytics([], today=TODAY)
    assert not empty.forecast_revenue()["available"]


def test_empty_data_does_not_crash():
    a = Analytics([], today=TODAY)
    assert a.summary()["profit"] == 0
    assert a.recommendations()
    assert "don't see any transactions" in RuleAssistant(a).respond("How much did I spend this month?")[0]


def test_tools_add_formatted_amounts_and_reject_bad_input():
    a = make()
    r = run_tool(a, "get_profit", {"month": "last_month"})
    assert r["profit_inr"].startswith("₹")
    assert "error" in run_tool(a, "nope", {})
    assert "error" in run_tool(a, "get_profit", {"month": "banana"})
    assert "error" in run_tool(a, "get_profit", {"bad_arg": 1})


def test_parse_scenario():
    cats = ["Marketing", "Inventory"]
    assert parse_scenario("If I reduce my monthly expenses by ₹5,000, what happens to my profit?", cats) == {"expense_change_amount": -5000.0}
    assert parse_scenario("What happens if I increase my price by 5%?", cats) == {"price_change_pct": 5.0}
    assert parse_scenario("What if I reduce marketing expenses by ₹2,000?", cats) == {"expense_change_amount": -2000.0, "category": "Marketing"}
    assert parse_scenario("what if sales increase by 10%", cats) == {"sales_change_pct": 10.0}
    assert parse_scenario("What can I do to increase my profit?", cats) is None


QUESTIONS = [
    "How much did I spend this month?",
    "What was my profit last month?",
    "Why is my profit lower this month?",
    "Which expense is increasing the most?",
    "What can I do to increase my profit?",
    "show me how",
    "If I reduce my monthly expenses by ₹5,000, what happens to my profit?",
    "What happens if I increase my price by 5%?",
    "How much did I spend on marketing this month?",
    "How is my business doing?",
    "What could my revenue look like next month?",
    "What is my profit margin?",
    "Show my top expenses",
    "Where does my revenue come from?",
    "How much revenue did I make in September?",
]


def test_every_example_question_gets_a_real_answer():
    for q in QUESTIONS:
        answer, tools = RuleAssistant(make()).respond(q)
        assert answer and "₹" in answer or "Try:" not in answer, q
        assert tools, f"no tool used for: {q}"
        assert "I can answer questions about your numbers" not in answer, q


def test_answers_use_database_numbers():
    a = make()
    ans, _ = RuleAssistant(a).respond("What was my profit last month?")
    assert inr(a.summary("last_month")["profit"]) in ans
    ans, _ = RuleAssistant(a).respond("How much did I spend on marketing this month?")
    assert inr(a.category_total("Marketing")["amount"]) in ans


def test_shift_month():
    assert shift_month("2026-01", -1) == "2025-12"
    assert shift_month("2026-12", 1) == "2027-01"


if __name__ == "__main__":
    failed = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except Exception as exc:  # noqa: BLE001
                failed += 1
                print("FAIL", name, "->", type(exc).__name__, exc)
    sys.exit(1 if failed else 0)
