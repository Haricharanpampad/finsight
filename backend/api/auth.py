from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import get_current_business, get_current_user
from database.connection import get_db
from models.business import Business
from models.user import User
from schemas.user import BusinessOut, LoginIn, RegisterIn, TokenOut, UserOut
from utils.ratelimit import RateLimiter
from utils.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

_auth_limiter = RateLimiter(max_calls=10, per_seconds=60)
_DUMMY_HASH = hash_password("not-a-real-password")  # keeps login timing similar for unknown emails


def _user_out(user: User, business: Business | None) -> UserOut:
    return UserOut(id=user.id, name=user.name, email=user.email,
                   business=BusinessOut.model_validate(business) if business else None)


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)):
    _auth_limiter.check(f"register:{request.client.host if request.client else 'unknown'}")
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")
    user = User(name=body.name.strip(), email=email, password_hash=hash_password(body.password))
    business = Business(business_name=body.business_name.strip(), business_type=body.business_type.strip() or "General")
    user.businesses.append(business)
    db.add(user)
    db.commit()
    db.refresh(user)
    db.refresh(business)
    return TokenOut(access_token=create_access_token(user.id), user=_user_out(user, business))


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    _auth_limiter.check(f"login:{request.client.host if request.client else 'unknown'}")
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    ok = verify_password(body.password, user.password_hash if user else _DUMMY_HASH)
    if not user or not ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
    business = db.scalar(select(Business).where(Business.user_id == user.id).order_by(Business.id))
    return TokenOut(access_token=create_access_token(user.id), user=_user_out(user, business))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user), business: Business = Depends(get_current_business)):
    return _user_out(user, business)
