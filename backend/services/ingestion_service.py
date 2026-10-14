"""Universal Ingestion Service for FinSight.

Parses transactions from CSV, Excel (.xlsx), and standard PDF bank statements.
Uses fuzzy column matching to normalize date, description, credit, debit,
amount, and type into the standard FinSight Transaction schema.
"""
from __future__ import annotations

import io
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

import pandas as pd
from pydantic import ValidationError

from schemas.transaction import TransactionIn

# Common column name aliases mapped to canonical keys
COLUMN_PATTERNS = {
    "date": [
        r"(^|_)(date|dt|txn_?date|trans_?date|transaction_?date|value_?date|value_?dt|posting_?date|post_?date|booking_?date)($|_)",
    ],
    "description": [
        r"(^|_)(description|narration|particulars|details|transaction_?details|remarks|memo|payee|merchant|notes?|title)($|_)",
    ],
    "credit": [
        r"(^|_)(credit|credit_?amt|credit_?amount|cr|deposit|deposits|inflow|received|receipts?|cr_?amount)($|_)",
        r"(credit|deposit)",
    ],
    "debit": [
        r"(^|_)(debit|debit_?amt|debit_?amount|dr|withdrawal|withdrawals|outflow|spent|payment|payments?|dr_?amount|paid)($|_)",
        r"(debit|withdrawal)",
    ],
    "amount": [
        r"(^|_)(amount|txn_?amount|transaction_?amount|net_?amount|trans_?amount|value|total)($|_)",
    ],
    "type": [
        r"(^|_)(type|txn_?type|transaction_?type|dr_?cr|cr_?dr|flow|direction|entry_?type)($|_)",
    ],
    "category": [
        r"(^|_)(category|expense_?category|source|classification|tag|head)($|_)",
    ],
    "payment_method": [
        r"(^|_)(payment_?method|method|mode|channel|payment_?mode|payment_?type)($|_)",
    ],
    "balance": [
        r"(^|_)(balance|closing_?balance|running_?balance|avail_?balance|net_?balance)($|_)",
        r"balance",
    ],
}

CATEGORY_KEYWORDS = {
    "expense": [
        ("Salaries", [r"\bsalary\b", r"\bsalaries\b", r"\bpayroll\b", r"\bstipend\b", r"\bwages?\b"]),
        ("Rent", [r"\brent\b", r"\blease\b", r"\blandlord\b"]),
        ("Utilities", [r"\belectricity\b", r"\bbescom\b", r"\bwater\b", r"\bwifi\b", r"\bbroadband\b",
                       r"\bairtel\b", r"\bjio\b", r"\binternet\b", r"\bpower\b", r"\bgas bill\b"]),
        ("Marketing", [r"\bgoogle ads\b", r"\badwords\b", r"\bfacebook\b", r"\bmeta ads\b",
                       r"\binstagram\b", r"\bmarketing\b", r"\badvert\b", r"\bcanva\b", r"\bhootsuite\b"]),
        ("Transport", [r"\buber\b", r"\bola\b", r"\bfuel\b", r"\bpetrol\b", r"\bdiesel\b",
                       r"\bhpcl\b", r"\bbpcl\b", r"\bioc\b", r"\bparking\b", r"\btoll\b",
                       r"\bfastag\b", r"\bflight\b", r"\bindigo\b", r"\birctc\b", r"\brailway\b"]),
        ("Inventory", [r"\bvendor\b", r"\bsupplier\b", r"\braw material\b", r"\bwholesale purchase\b",
                       r"\bstock\b", r"\binventory\b", r"\bgoods purchase\b"]),
        ("Maintenance", [r"\brepair\b", r"\bhardware\b", r"\bsoftware\b", r"\baws\b", r"\bazure\b",
                         r"\bhosting\b", r"\bgithub\b", r"\bdomain\b", r"\bmaintenance\b", r"\bcleaning\b"]),
        ("Taxes", [r"\bgst\b", r"\btds\b", r"\bincome tax\b", r"\bchallan\b", r"\btax payment\b"]),
    ],
    "revenue": [
        ("Online orders", [r"\brazorpay\b", r"\bstripe\b", r"\bshopify\b", r"\bswiggy\b", r"\bzomato\b", r"\be-?commerce\b"]),
        ("Retail sales", [r"\bpos sale\b", r"\bstore sale\b", r"\bcounter sale\b", r"\bupi collection\b", r"\bqr collection\b"]),
        ("Wholesale", [r"\bwholesale\b", r"\bbulk\b", r"\bb2b\b", r"\bdistributor\b"]),
        ("Services", [r"\bconsulting\b", r"\bservice fee\b", r"\bclient payment\b", r"\bretainer\b"]),
    ],
}


def _clean_header(name: Any) -> str:
    """Normalize column header text: lowercased, alpha-numeric and underscores only."""
    text = str(name).strip().lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", "_", text)
    return text.strip("_")


def fuzzy_match_columns(columns: list[Any]) -> dict[str, str]:
    """Maps recognized canonical keys ('date', 'description', etc.) to actual column names."""
    mapping: dict[str, str] = {}
    cleaned = {col: _clean_header(col) for col in columns if str(col).strip() != ""}

    # Priority order for canonical keys
    for canonical, patterns in COLUMN_PATTERNS.items():
        for original, clean in cleaned.items():
            if canonical in mapping:
                break
            for pat in patterns:
                if re.search(pat, clean):
                    mapping[canonical] = original
                    break

    return mapping


def _clean_amount_str(val: Any) -> tuple[Decimal | None, str | None]:
    """Extract numeric Decimal amount and optional credit/debit sign indicator."""
    if val is None or pd.isna(val):
        return None, None
    s = str(val).strip()
    if not s or s == "-":
        return None, None

    # Check for trailing (Cr/Dr) or leading +/-
    indicator = None
    if re.search(r"\bcr\b|\bcredit\b", s, re.IGNORECASE):
        indicator = "credit"
    elif re.search(r"\bdr\b|\bdebit\b", s, re.IGNORECASE):
        indicator = "debit"

    # Check for accounting parentheses e.g. (1,200.50)
    is_negative = False
    if s.startswith("(") and s.endswith(")"):
        is_negative = True
        s = s[1:-1]
    elif s.startswith("-"):
        is_negative = True
        s = s[1:]

    # Remove currency symbols (₹, $, €, £, Rs, INR) and commas
    s = re.sub(r"[^\d.]", "", s)
    if not s or s == ".":
        return None, None

    try:
        amt = Decimal(s)
        if amt < 0:
            is_negative = True
            amt = abs(amt)
        if is_negative and indicator is None:
            indicator = "debit"
        return amt, indicator
    except (InvalidOperation, ValueError):
        return None, None


def _parse_date(val: Any) -> date | None:
    """Parse date robustly, handling Indian/UK (day-first) and US formats."""
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (datetime, pd.Timestamp)):
        return val.date()
    if isinstance(val, date):
        return val

    s = str(val).strip()
    if not s:
        return None

    # Remove extra timestamp if any: e.g. "2026-10-14 14:30:00" -> "2026-10-14"
    date_part = s.split(" ")[0].split("T")[0]
    formats = [
        "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
        "%Y-%m-%d", "%Y/%m/%d",
        "%d/%m/%y", "%d-%m-%y",
        "%d %b %Y", "%d-%b-%Y", "%d %B %Y",
        "%b %d, %Y", "%B %d, %Y",
        "%m/%d/%Y", "%m-%d-%Y"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_part, fmt).date()
        except ValueError:
            pass

    try:
        dt = pd.to_datetime(s, dayfirst=True)
        return dt.date()
    except Exception:
        return None


def _infer_category(description: str, kind: Literal["revenue", "expense"]) -> str:
    """Infer category from description keywords, with safe defaults."""
    desc = description.lower()
    for cat_name, patterns in CATEGORY_KEYWORDS.get(kind, []):
        for pat in patterns:
            if re.search(pat, desc):
                return cat_name
    return "Other"


def _infer_payment_method(description: str, explicit_method: str = "") -> str:
    """Infer payment method from explicit column or description."""
    if explicit_method and explicit_method.strip():
        m = explicit_method.strip()
        if len(m) <= 40:
            return m

    desc = description.lower()
    if "upi" in desc or "@" in desc or "vpa" in desc:
        return "UPI"
    if any(k in desc for k in ["neft", "rtgs", "imps", "ach", "transfer", "wire"]):
        return "Bank transfer"
    if any(k in desc for k in ["card", "pos", "visa", "mastercard", "rupay"]):
        return "Card"
    if any(k in desc for k in ["cash", "atm"]):
        return "Cash"
    return "Bank transfer"


def _find_header_row_index(df_raw: pd.DataFrame) -> int | None:
    """Find the index of the row that looks most like a transaction header."""
    for idx, row in df_raw.head(25).iterrows():
        row_str = " ".join([str(val).lower() for val in row if pd.notna(val)])
        has_date = bool(re.search(r"\b(date|dt|txn_?date|trans_?date)\b", row_str))
        has_amount = bool(re.search(r"\b(amount|credit|debit|deposit|withdrawal|dr|cr|balance)\b", row_str))
        has_desc = bool(re.search(r"\b(particulars|narration|description|details|memo)\b", row_str))
        if has_date and (has_amount or has_desc):
            return int(idx)
    return None


def parse_csv_file(file_bytes: bytes) -> pd.DataFrame:
    """Read CSV with multiple encodings and robust header row detection."""
    encodings = ["utf-8-sig", "utf-8", "latin1", "cp1252"]
    df = None
    last_err = None

    for enc in encodings:
        try:
            text = file_bytes.decode(enc)
            lines = text.splitlines()
            if not lines:
                continue

            header_idx = 0
            for i, line in enumerate(lines[:35]):
                line_lower = line.lower()
                has_date = bool(re.search(r"\b(date|dt|txn_?date|trans_?date)\b", line_lower))
                has_amt_or_desc = bool(re.search(r"\b(amount|debit|credit|deposit|withdrawal|particulars|narration|description|balance|dr|cr)\b", line_lower))
                if has_date and has_amt_or_desc:
                    header_idx = i
                    break

            csv_text = "\n".join(lines[header_idx:])
            try:
                df = pd.read_csv(io.StringIO(csv_text), dtype=str)
            except Exception:
                df = pd.read_csv(io.StringIO(csv_text), sep=None, engine="python", dtype=str)
            break
        except Exception as e:
            last_err = e

    if df is None:
        raise ValueError(f"Unable to read CSV file: {last_err or 'corrupted or empty'}")
    return df


def parse_excel_file(file_bytes: bytes) -> pd.DataFrame:
    """Read Excel file (.xlsx) with header row detection."""
    try:
        raw = pd.read_excel(io.BytesIO(file_bytes), header=None, dtype=str)
    except Exception as e:
        raise ValueError(f"Unable to parse Excel file: {e}")

    header_idx = _find_header_row_index(raw)
    if header_idx is not None and header_idx > 0:
        return pd.read_excel(io.BytesIO(file_bytes), skiprows=header_idx, dtype=str)
    return pd.read_excel(io.BytesIO(file_bytes), dtype=str)


def parse_pdf_file(file_bytes: bytes) -> pd.DataFrame:
    """Extract tabular transaction data from standard PDF bank statements using pdfplumber."""
    try:
        import pdfplumber
    except ImportError:
        raise ValueError("pdfplumber is not installed on the server.")

    all_rows: list[list[str]] = []
    header: list[str] | None = None

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        if not pdf.pages:
            raise ValueError("The uploaded PDF has no readable pages.")

        for page in pdf.pages:
            tables = page.extract_tables()
            if not tables:
                # Try table extraction with explicit text strategies if line borders are missing
                tables = page.extract_tables(table_settings={
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "snap_tolerance": 3,
                })

            for table in tables:
                if not table:
                    continue
                for raw_row in table:
                    # Clean newlines and nulls within cells
                    row = [re.sub(r"\s+", " ", str(cell).strip()) if cell is not None else "" for cell in raw_row]
                    if not any(row):
                        continue

                    # If header hasn't been set, test if this row looks like a header
                    if header is None:
                        row_str = " ".join(row).lower()
                        has_date = bool(re.search(r"\b(date|dt|txn_?date)\b", row_str))
                        has_amt = bool(re.search(r"\b(amount|credit|debit|deposit|withdrawal|balance)\b", row_str))
                        if has_date and has_amt:
                            header = row
                            continue
                    else:
                        # Skip repeated header row on subsequent pages
                        if row == header or " ".join(row).lower() == " ".join(header).lower():
                            continue
                        all_rows.append(row)

    if not header or not all_rows:
        raise ValueError(
            "Could not detect a standard tabular bank statement in the uploaded PDF. "
            "Please ensure the statement includes Date, Description, and Amount/Debit/Credit columns."
        )

    # Pad or trim rows to match header length
    n_cols = len(header)
    cleaned_rows = []
    for r in all_rows:
        if len(r) < n_cols:
            r = r + [""] * (n_cols - len(r))
        elif len(r) > n_cols:
            r = r[:n_cols]
        cleaned_rows.append(r)

    return pd.DataFrame(cleaned_rows, columns=header)


def process_uploaded_file(file_bytes: bytes, filename: str) -> list[dict[str, Any]]:
    """Parse uploaded file and convert to normalized, validated FinSight transactions."""
    lower_name = filename.lower()
    if lower_name.endswith(".csv"):
        df = parse_csv_file(file_bytes)
    elif lower_name.endswith((".xlsx", ".xls")):
        df = parse_excel_file(file_bytes)
    elif lower_name.endswith(".pdf"):
        df = parse_pdf_file(file_bytes)
    else:
        raise ValueError("Unsupported file format. Please upload a .csv, .xlsx, or .pdf file.")

    # Clean DataFrame columns
    df.columns = [str(c).strip() for c in df.columns]
    mapping = fuzzy_match_columns(list(df.columns))

    if "date" not in mapping:
        raise ValueError(f"Could not find a 'Date' column in {filename}. Columns found: {list(df.columns)}")

    has_credit = "credit" in mapping
    has_debit = "debit" in mapping
    has_amount = "amount" in mapping

    if not (has_credit or has_debit or has_amount):
        raise ValueError(
            f"Could not find 'Credit', 'Debit', or 'Amount' columns in {filename}. "
            f"Columns found: {list(df.columns)}"
        )

    results: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        # Parse date
        raw_date = row.get(mapping["date"])
        tx_date = _parse_date(raw_date)
        if not tx_date:
            continue  # Skip header repeats, totals, or subtotal rows without valid date

        # Parse description
        desc_col = mapping.get("description")
        description = str(row.get(desc_col, "")).strip() if desc_col else ""
        if description.lower() in ("nan", "none", "null"):
            description = ""
        description = description[:255]

        # Determine Amount and Type (Revenue vs Expense)
        amt: Decimal | None = None
        tx_type: Literal["revenue", "expense"] | None = None

        if has_credit and has_debit:
            cr_val, _ = _clean_amount_str(row.get(mapping["credit"]))
            dr_val, _ = _clean_amount_str(row.get(mapping["debit"]))

            if cr_val and cr_val > 0:
                amt = cr_val
                tx_type = "revenue"
            elif dr_val and dr_val > 0:
                amt = dr_val
                tx_type = "expense"
        elif has_credit:
            cr_val, _ = _clean_amount_str(row.get(mapping["credit"]))
            if cr_val and cr_val > 0:
                amt = cr_val
                tx_type = "revenue"
        elif has_debit:
            dr_val, _ = _clean_amount_str(row.get(mapping["debit"]))
            if dr_val and dr_val > 0:
                amt = dr_val
                tx_type = "expense"

        if amt is None and has_amount:
            raw_amt_val = row.get(mapping["amount"])
            parsed_amt, indicator = _clean_amount_str(raw_amt_val)
            if parsed_amt and parsed_amt > 0:
                amt = parsed_amt
                # Check type column or indicator
                type_col = mapping.get("type")
                raw_type = str(row.get(type_col, "")).strip().lower() if type_col else ""

                if indicator == "credit" or raw_type in ("cr", "credit", "deposit", "revenue", "income"):
                    tx_type = "revenue"
                elif indicator == "debit" or raw_type in ("dr", "debit", "withdrawal", "expense", "payment"):
                    tx_type = "expense"
                else:
                    # Default: if description indicates payment/expense vs revenue
                    if any(k in description.lower() for k in ["salary", "rent", "bill", "paid to", "purchase", "tax", "fee"]):
                        tx_type = "expense"
                    elif any(k in description.lower() for k in ["received from", "sales", "interest", "refund"]):
                        tx_type = "revenue"
                    else:
                        tx_type = "expense"

        if amt is None or amt <= 0 or tx_type is None:
            continue

        # Category
        cat_col = mapping.get("category")
        explicit_cat = str(row.get(cat_col, "")).strip() if cat_col else ""
        if explicit_cat and explicit_cat.lower() not in ("nan", "none", "null"):
            category = explicit_cat[:80]
        else:
            category = _infer_category(description, tx_type)

        # Payment method
        pm_col = mapping.get("payment_method")
        explicit_pm = str(row.get(pm_col, "")).strip() if pm_col else ""
        payment_method = _infer_payment_method(description, explicit_pm)

        # Validate with TransactionIn to ensure Pydantic constraints
        try:
            validated = TransactionIn(
                type=tx_type,
                amount=amt,
                category=category,
                description=description,
                transaction_date=tx_date,
                payment_method=payment_method
            )
            item_dict = validated.model_dump()
            item_dict["amount"] = float(validated.amount)
            item_dict["transaction_date"] = validated.transaction_date.isoformat()
            results.append(item_dict)
        except ValidationError:
            continue

    if not results:
        raise ValueError(
            f"No valid transaction rows could be parsed from {filename}. "
            "Please check that the file has valid dates, amounts, and descriptions."
        )

    return results
