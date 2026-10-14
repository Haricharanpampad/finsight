"""Expense/Revenue management: database access for transactions.

Every function takes a `business_id` and filters by it, so one business can never read or
change another business's data, even by guessing IDs.
"""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from models.transaction import Transaction
from schemas.transaction import TransactionIn
from services.analytics_service import Analytics, shift_month

DEFAULT_EXPENSE_CATEGORIES = ["Inventory", "Rent", "Salaries", "Marketing", "Utilities", "Transport", "Maintenance", "Taxes", "Other"]
DEFAULT_REVENUE_SOURCES = ["Retail sales", "Online orders", "Wholesale", "Services", "Other"]


def today_local() -> date:
    try:
        return datetime.now(ZoneInfo(settings.TIMEZONE)).date()
    except Exception:  # unknown timezone / missing tzdata
        return date.today()


def load_analytics(db: Session, business_id: int, today: date | None = None) -> Analytics:
    rows = db.execute(
        select(Transaction.type, Transaction.amount, Transaction.category, Transaction.transaction_date)
        .where(Transaction.business_id == business_id)
    ).all()
    return Analytics(
        [{"type": r.type, "amount": float(r.amount), "category": r.category, "date": r.transaction_date} for r in rows],
        today=today or today_local(),
    )


def list_transactions(
    db: Session, business_id: int, kind: str | None = None, category: str | None = None,
    month: str | None = None, limit: int = 200, offset: int = 0,
) -> list[Transaction]:
    q = select(Transaction).where(Transaction.business_id == business_id)
    if kind:
        q = q.where(Transaction.type == kind)
    if category:
        q = q.where(Transaction.category == category)
    if month:
        start = date(int(month[:4]), int(month[5:7]), 1)
        end_ym = shift_month(month, 1)
        q = q.where(Transaction.transaction_date >= start,
                    Transaction.transaction_date < date(int(end_ym[:4]), int(end_ym[5:7]), 1))
    q = q.order_by(Transaction.transaction_date.desc(), Transaction.id.desc()).limit(limit).offset(offset)
    return list(db.scalars(q))


def get_transaction(db: Session, business_id: int, tx_id: int) -> Transaction | None:
    return db.scalar(select(Transaction).where(Transaction.id == tx_id, Transaction.business_id == business_id))


def create_transaction(db: Session, business_id: int, data: TransactionIn) -> Transaction:
    tx = Transaction(business_id=business_id, **data.model_dump())
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def update_transaction(db: Session, tx: Transaction, data: TransactionIn) -> Transaction:
    for field, value in data.model_dump().items():
        setattr(tx, field, value)
    db.commit()
    db.refresh(tx)
    return tx


def delete_transaction(db: Session, tx: Transaction) -> None:
    db.delete(tx)
    db.commit()


def category_options(db: Session, business_id: int, kind: str) -> list[str]:
    used = db.scalars(
        select(Transaction.category).where(Transaction.business_id == business_id, Transaction.type == kind).distinct()
    ).all()
    defaults = DEFAULT_EXPENSE_CATEGORIES if kind == "expense" else DEFAULT_REVENUE_SOURCES
    return sorted(set(defaults) | set(used))
