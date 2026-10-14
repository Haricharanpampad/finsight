"""Business recommendation engine (the rules live in Analytics.recommendations)."""
from services.analytics_service import Analytics


def get_recommendations(analytics: Analytics, month: str | None = None) -> list[dict]:
    return analytics.recommendations(month)


def top_insights(analytics: Analytics, n: int = 2) -> list[dict]:
    """The most important suggestions first: warnings, then watch items, then info."""
    order = {"warning": 0, "watch": 1, "info": 2, "good": 3}
    recs = sorted(analytics.recommendations(), key=lambda r: order.get(r["severity"], 9))
    return recs[:n]
