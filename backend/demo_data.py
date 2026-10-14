"""Generates realistic demo transactions (pure Python, no database) for the seed script and tests."""
import random
from datetime import date

from services.analytics_service import shift_month

REVENUE_SOURCES = {"Retail sales": 0.58, "Online orders": 0.27, "Wholesale": 0.15}


def generate_demo_rows(today: date | None = None, months: int = 7, seed: int = 42) -> list[dict]:
    """Rows for `months` months ending with the current (partial) month.

    The story in the data: revenue grows slowly, but Inventory spending jumps last month and keeps
    rising, so FinSight has something real to explain.
    """
    rng = random.Random(seed)
    today = today or date.today()
    current = f"{today.year:04d}-{today.month:02d}"
    rows: list[dict] = []

    for back in range(months - 1, -1, -1):
        ym = shift_month(current, -back)
        year, month = map(int, ym.split("-"))
        step = months - 1 - back  # 0 = oldest month

        monthly_revenue = 105_000 + step * 3_500 + rng.randint(-2_500, 2_500)
        inventory = 28_000 + step * 600 + {1: 7_500, 0: 9_000}.get(back, 0)  # costs jump in the last two months
        expenses = {
            "Inventory": inventory,
            "Rent": 15_000,
            "Salaries": 18_000,
            "Marketing": 6_000 + step * 250,
            "Utilities": 3_200 + rng.randint(-300, 300),
            "Transport": 2_800 + rng.randint(-200, 200),
        }

        def add(kind, amount, category, day, desc, method):
            if day > 28:
                day = 28
            d = date(year, month, day)
            if d <= today:
                rows.append({"type": kind, "amount": round(amount, 2), "category": category,
                             "description": desc, "date": d, "payment_method": method})

        for source, share in REVENUE_SOURCES.items():
            n = {"Retail sales": 10, "Online orders": 5, "Wholesale": 3}[source]
            total = monthly_revenue * share
            for i in range(n):
                day = 1 + int((i + rng.random() * 0.8) * 27 / n)
                add("revenue", total / n * rng.uniform(0.9, 1.1), source, day, f"{source} batch {i + 1}",
                    rng.choice(["UPI", "Cash", "Card"]))

        for i, day in enumerate((3, 9, 16, 23)):
            add("expense", expenses["Inventory"] / 4, "Inventory", day, f"Stock purchase {i + 1}", "Bank transfer")
        add("expense", expenses["Rent"], "Rent", 1, "Shop rent", "Bank transfer")
        add("expense", expenses["Salaries"], "Salaries", 28, "Staff salaries", "Bank transfer")
        for i, day in enumerate((4, 14, 22)):
            add("expense", expenses["Marketing"] / 3, "Marketing", day, f"Instagram / flyers {i + 1}", "UPI")
        add("expense", expenses["Utilities"], "Utilities", 9, "Electricity + internet", "UPI")
        add("expense", expenses["Transport"], "Transport", 12, "Delivery fuel", "Cash")
    return rows
