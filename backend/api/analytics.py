import calendar

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.deps import get_current_business
from database.connection import get_db
from models.business import Business
from services.analytics_service import Analytics, month_label, shift_month
from services.financial_service import load_analytics
from services.recommendation_service import top_insights

router = APIRouter(prefix="/api", tags=["analytics"])


def _analytics(db: Session, business: Business) -> Analytics:
    return load_analytics(db, business.id)


def _month(a: Analytics, month: str | None) -> str:
    try:
        return a.resolve_month(month)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc


@router.get("/dashboard")
def dashboard(business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    """Everything the dashboard screen needs in one call (this month so far)."""
    a = _analytics(db, business)
    summary = a.summary()
    cmp = a.compare_months()
    last_full = shift_month(a.current_month, -1)
    return {
        "business": business.business_name,
        "month": a.current_month,
        "month_label": month_label(a.current_month),
        "through_day": a.today.day,
        "days_in_month": calendar.monthrange(a.today.year, a.today.month)[1],
        "revenue": summary["revenue"],
        "expenses": summary["expenses"],
        "profit": summary["profit"],
        "profit_margin": summary["profit_margin_pct"],
        "vs_last_period": cmp,
        "last_full_month": a.summary(last_full) | {"label": month_label(last_full)},
        "trend": a.monthly_trend(6),
        "top_expenses": a.top_expenses(n=5),
        "revenue_sources": a.by_category("revenue"),
        "expense_growth": a.category_growth()[:5],
        "insights": top_insights(a, 2),
        "has_data": bool(len(a.df)),
    }


@router.get("/analytics/monthly")
def monthly(months: int = Query(6, ge=1, le=24), business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    return {"trend": _analytics(db, business).monthly_trend(months)}


@router.get("/analytics/profit")
def profit(month: str | None = None, business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    a = _analytics(db, business)
    return a.compare_months(_month(a, month))


@router.get("/analytics/expenses")
def expenses(month: str | None = None, business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    a = _analytics(db, business)
    m = _month(a, month)
    return {"month": m, "categories": a.by_category("expense", m), "growth": a.category_growth(m)}


@router.get("/analytics/insights")
def insights(month: str | None = None, business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    a = _analytics(db, business)
    return {"recommendations": a.recommendations(_month(a, month))}


@router.get("/analytics/forecast")
def forecast(months_ahead: int = Query(1, ge=1, le=6), business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    return _analytics(db, business).forecast_revenue(months_ahead)


class ScenarioIn(BaseModel):
    price_change_pct: float = Field(default=0, ge=-100, le=500)
    sales_change_pct: float = Field(default=0, ge=-100, le=500)
    expense_change_amount: float = Field(default=0, ge=-10_000_000, le=10_000_000)
    expense_change_pct: float = Field(default=0, ge=-100, le=500)
    category: str | None = Field(default=None, max_length=80)


@router.post("/analytics/scenario")
def scenario(body: ScenarioIn, business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    """What-if analysis (projection, not a prediction)."""
    return _analytics(db, business).scenario(**body.model_dump())
