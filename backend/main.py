"""FinSight API entry point.   Run:  uvicorn main:app --reload"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import models  # noqa: F401  (registers the tables with SQLAlchemy)
from api import analytics, assistant, auth, transactions
from config import settings
from database.connection import Base, engine

log = logging.getLogger("finsight")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)  # for production, manage schema changes with Alembic migrations
    if settings.JWT_SECRET in ("change-me", "dev-only-change-me"):
        log.warning("JWT_SECRET is not set to a private value - set it in .env before deploying.")
    log.info("Assistant mode: %s", "Gemini" if settings.GEMINI_API_KEY else "built-in rules (no GEMINI_API_KEY)")
    yield


app = FastAPI(title="FinSight API", version="1.0.0", description="AI business copilot for small-business finances.", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

for module in (auth, transactions, analytics, assistant):
    app.include_router(module.router)


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok", "assistant": "gemini" if settings.GEMINI_API_KEY else "rules"}
