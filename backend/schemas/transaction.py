from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TransactionIn(BaseModel):
    type: Literal["revenue", "expense"]
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    category: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=255)
    transaction_date: date
    payment_method: str = Field(default="", max_length=40)


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    amount: float
    category: str
    description: str
    transaction_date: date
    payment_method: str


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(max_length=4000)


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)


class ChatOut(BaseModel):
    answer: str
    tools_used: list[str]
    mode: str  # "gemini" or "rules"
