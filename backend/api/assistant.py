from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_current_business, get_current_user
from database.connection import get_db
from models.business import Business
from models.user import User
from schemas.transaction import ChatIn, ChatOut
from services.ai_service import answer_question
from utils.ratelimit import RateLimiter

router = APIRouter(prefix="/api/assistant", tags=["assistant"])

_chat_limiter = RateLimiter(max_calls=30, per_seconds=60)


@router.post("/chat", response_model=ChatOut)
def chat(
    body: ChatIn,
    user: User = Depends(get_current_user),
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    """Natural-language question -> AI picks tools -> analytics engine computes -> AI explains."""
    _chat_limiter.check(f"chat:{user.id}")
    return answer_question(db, business.id, body.message, body.history)
