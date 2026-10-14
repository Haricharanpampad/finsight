"""Shared FastAPI dependencies: who is calling, and which business they own."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.connection import get_db
from models.business import Business
from models.user import User
from utils.security import decode_access_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
) -> User:
    user_id = decode_access_token(creds.credentials) if creds else None
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please log in again.", headers={"WWW-Authenticate": "Bearer"})
    return user


def get_current_business(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Business:
    """The business is always taken from the logged-in user - never from an ID in the URL."""
    business = db.scalar(select(Business).where(Business.user_id == user.id).order_by(Business.id))
    if business is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No business profile found for this account.")
    return business
