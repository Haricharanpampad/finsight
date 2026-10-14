"""Create a demo account with ~7 months of realistic data.

    python seed.py            # create demo account (does nothing if it already exists)
    python seed.py --reset    # delete and recreate it

Login:  demo@finsight.app / demo12345
"""
import sys
from decimal import Decimal

from sqlalchemy import select

import models  # noqa: F401
from database.connection import Base, SessionLocal, engine
from demo_data import generate_demo_rows
from models.business import Business
from models.transaction import Transaction
from models.user import User
from services.financial_service import today_local
from utils.security import hash_password

DEMO_EMAIL = "demo@finsight.app"
DEMO_PASSWORD = "demo12345"


def seed(reset: bool = False) -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if existing and not reset:
            print(f"Demo account already exists ({DEMO_EMAIL}). Use --reset to recreate it.")
            return
        if existing:
            db.delete(existing)
            db.commit()

        user = User(name="Ravi", email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD))
        business = Business(business_name="Ravi General Store", business_type="Retail")
        user.businesses.append(business)
        db.add(user)
        db.commit()
        db.refresh(business)

        rows = generate_demo_rows(today_local())
        db.add_all(
            Transaction(
                business_id=business.id, type=r["type"], amount=Decimal(str(r["amount"])), category=r["category"],
                description=r["description"], transaction_date=r["date"], payment_method=r["payment_method"],
            )
            for r in rows
        )
        db.commit()
        print(f"Created demo account with {len(rows)} transactions.\n  email:    {DEMO_EMAIL}\n  password: {DEMO_PASSWORD}")


if __name__ == "__main__":
    seed(reset="--reset" in sys.argv)
