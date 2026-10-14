"""AI Service: glue between the API and the AI orchestration layer."""
from sqlalchemy.orm import Session

from ai.agent import FinSightAgent
from config import settings
from schemas.transaction import ChatTurn
from services.financial_service import load_analytics


def answer_question(db: Session, business_id: int, message: str, history: list[ChatTurn]) -> dict:
    analytics = load_analytics(db, business_id)  # only this business's transactions
    agent = FinSightAgent(analytics, api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)
    return agent.chat(message, [t.model_dump() for t in history])
