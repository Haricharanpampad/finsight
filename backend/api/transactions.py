from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from api.deps import get_current_business
from database.connection import get_db
from models.business import Business
from schemas.transaction import TransactionIn, TransactionOut
from services import financial_service as fs
from services.ingestion_service import process_uploaded_file

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


@router.post("/upload")
async def upload_transactions(
    file: UploadFile = File(...),
    business: Business = Depends(get_current_business),
):
    """Parse CSV, Excel, or PDF bank statements into normalized transactions for preview."""
    if not file.filename:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No file provided.")

    ext = file.filename.lower().split(".")[-1]
    if ext not in ("csv", "xlsx", "xls", "pdf"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unsupported file format '.{ext}'. Supported formats are .csv, .xlsx, .pdf."
        )

    try:
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "The uploaded file is empty.")
        if len(content) > 15 * 1024 * 1024:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "File size exceeds 15 MB limit.")

        items = process_uploaded_file(content, file.filename)
        return {
            "filename": file.filename,
            "total": len(items),
            "items": items,
        }
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Error processing file: {str(e)}")


@router.post("/bulk", response_model=list[TransactionOut], status_code=status.HTTP_201_CREATED)
def bulk_create(
    items: list[TransactionIn],
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Bulk insert verified transactions tied to the authenticated user's business ID."""
    if not items:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No transactions provided for insertion.")
    if len(items) > 1000:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot bulk import more than 1000 transactions at once.")
    return fs.bulk_create_transactions(db, business.id, items)


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
