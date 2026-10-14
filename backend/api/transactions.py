from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from api.deps import get_current_business
from database.connection import get_db
from models.business import Business
from schemas.transaction import TransactionIn, TransactionOut
from services import financial_service as fs

router = APIRouter(prefix="/api/transactions", tags=["transactions"])

Kind = Literal["revenue", "expense"]


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    type: Kind | None = None,
    category: str | None = None,
    month: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    return fs.list_transactions(db, business.id, type, category, month, limit, offset)


@router.get("/categories", response_model=list[str])
def categories(type: Kind = "expense", business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    return fs.category_options(db, business.id, type)


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create(body: TransactionIn, business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    return fs.create_transaction(db, business.id, body)


def _owned_or_404(db: Session, business: Business, tx_id: int):
    tx = fs.get_transaction(db, business.id, tx_id)
    if tx is None:  # 404 (not 403) so other businesses' IDs aren't revealed
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Transaction not found.")
    return tx


@router.put("/{tx_id}", response_model=TransactionOut)
def update(tx_id: int, body: TransactionIn, business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    return fs.update_transaction(db, _owned_or_404(db, business, tx_id), body)


@router.delete("/{tx_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(tx_id: int, business: Business = Depends(get_current_business), db: Session = Depends(get_db)):
    fs.delete_transaction(db, _owned_or_404(db, business, tx_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
