"""Tests for Universal Ingestion (CSV, Excel, and PDF bank statements).

Run with: pytest backend/tests/test_ingestion.py
"""
import io
import os
import sys
from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.ingestion_service import (
    _clean_amount_str,
    _parse_date,
    fuzzy_match_columns,
    process_uploaded_file,
)


def test_fuzzy_match_columns_standard():
    cols = ["Txn Date", "Narration", "Withdrawal (Dr)", "Deposit (Cr)", "Closing Balance"]
    mapping = fuzzy_match_columns(cols)
    assert mapping["date"] == "Txn Date"
    assert mapping["description"] == "Narration"
    assert mapping["debit"] == "Withdrawal (Dr)"
    assert mapping["credit"] == "Deposit (Cr)"
    assert mapping["balance"] == "Closing Balance"


def test_fuzzy_match_columns_alternate_bank_format():
    cols = ["Value_Date", "Transaction_Details", "Spent", "Received"]
    mapping = fuzzy_match_columns(cols)
    assert mapping["date"] == "Value_Date"
    assert mapping["description"] == "Transaction_Details"
    assert mapping["debit"] == "Spent"
    assert mapping["credit"] == "Received"


def test_clean_amount_parsing():
    amt, ind = _clean_amount_str("₹ 12,500.50")
    assert amt == Decimal("12500.50")
    assert ind is None

    amt, ind = _clean_amount_str("(4,200.00)")
    assert amt == Decimal("4200.00")
    assert ind == "debit"

    amt, ind = _clean_amount_str("5,000.00 Cr")
    assert amt == Decimal("5000.00")
    assert ind == "credit"

    amt, ind = _clean_amount_str("3,100.00 Dr")
    assert amt == Decimal("3100.00")
    assert ind == "debit"


def test_date_parsing():
    assert _parse_date("14/10/2026") == date(2026, 10, 14)
    assert _parse_date("2026-10-14") == date(2026, 10, 14)
    assert _parse_date("14-Oct-2026") == date(2026, 10, 14)
    assert _parse_date("Oct 14, 2026") == date(2026, 10, 14)


def test_process_csv_with_credit_debit():
    csv_data = """Date,Narration,Debit,Credit,Balance
14/10/2026,Office Rent payment,45000,,155000
15/10/2026,UPI customer QR collection,,12000,167000
16/10/2026,Swiggy food order,450,,166550
"""
    items = process_uploaded_file(csv_data.encode("utf-8"), "statement.csv")
    assert len(items) == 3

    # Rent -> expense, Rent category
    assert items[0]["type"] == "expense"
    assert items[0]["amount"] == 45000.0
    assert items[0]["category"] == "Rent"
    assert items[0]["transaction_date"] == "2026-10-14"

    # Customer QR -> revenue, Retail sales
    assert items[1]["type"] == "revenue"
    assert items[1]["amount"] == 12000.0
    assert items[1]["category"] == "Retail sales"
    assert items[1]["payment_method"] == "UPI"

    # Food order -> expense, Other
    assert items[2]["type"] == "expense"
    assert items[2]["amount"] == 450.0


def test_process_csv_with_header_preamble():
    csv_data = """HDFC Bank Statement
Account Number: 123456789
Period: 01-10-2026 to 14-10-2026

Date,Description,Amount,Type
10/10/2026,Google Ads campaign,8500,Dr
11/10/2026,Razorpay payout received,65000,Cr
"""
    items = process_uploaded_file(csv_data.encode("utf-8"), "hdfc.csv")
    assert len(items) == 2

    assert items[0]["type"] == "expense"
    assert items[0]["amount"] == 8500.0
    assert items[0]["category"] == "Marketing"

    assert items[1]["type"] == "revenue"
    assert items[1]["amount"] == 65000.0
    assert items[1]["category"] == "Online orders"


def test_process_excel_file():
    df = pd.DataFrame([
        {"Date": "2026-10-01", "Particulars": "Staff Salary transfer", "Debit": 85000, "Credit": None},
        {"Date": "2026-10-02", "Particulars": "Wholesale bulk buyer payment", "Debit": None, "Credit": 140000},
    ])
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    bio.seek(0)

    items = process_uploaded_file(bio.getvalue(), "accounts.xlsx")
    assert len(items) == 2
    assert items[0]["type"] == "expense"
    assert items[0]["category"] == "Salaries"
    assert items[0]["amount"] == 85000.0

    assert items[1]["type"] == "revenue"
    assert items[1]["category"] == "Wholesale"
    assert items[1]["amount"] == 140000.0


def test_reject_unsupported_extension():
    with pytest.raises(ValueError, match="Unsupported file format"):
        process_uploaded_file(b"test", "statement.exe")


def test_reject_empty_file():
    with pytest.raises(ValueError, match="Could not find a 'Date' column"):
        process_uploaded_file(b"col1,col2\n1,2", "dummy.csv")


def test_process_pdf_file_mock(monkeypatch):
    import pdfplumber

    class DummyPage:
        def extract_tables(self, *args, **kwargs):
            return [
                [
                    ["Txn Date", "Narration", "Debit", "Credit", "Balance"],
                    ["2026-10-05", "Office electricity bill payment", "3500.00", "", "96500.00"],
                    ["2026-10-06", "Consulting service retainer fee", "", "45000.00", "141500.00"],
                ]
            ]

    class DummyPdf:
        pages = [DummyPage()]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(pdfplumber, "open", lambda *args, **kwargs: DummyPdf())

    items = process_uploaded_file(b"%PDF-1.4 mock", "bank_statement.pdf")
    assert len(items) == 2

    assert items[0]["type"] == "expense"
    assert items[0]["amount"] == 3500.0
    assert items[0]["category"] == "Utilities"

    assert items[1]["type"] == "revenue"
    assert items[1]["amount"] == 45000.0
    assert items[1]["category"] == "Services"
