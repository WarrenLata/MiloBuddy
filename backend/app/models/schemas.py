from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PostExpenseRequest(BaseModel):
    amount: float
    currency: str = "EUR"
    description: Optional[str] = None


class TransactionOut(BaseModel):
    id: int
    amount: float
    currency: str
    timestamp: datetime
    description: Optional[str] = None


class GetBudgetResponse(BaseModel):
    monthly_budget: float
    total_spent: float
    remaining: float
    transactions: List[TransactionOut] = Field(default_factory=list)


class TrackBudgetRequest(BaseModel):
    amount: float


class TrackBudgetResponse(BaseModel):
    allowed: bool
    remaining_if_allowed: float


class PostGoalRequest(BaseModel):
    title: str
    target_amount: float


class GoalOut(BaseModel):
    id: int
    title: str
    target_amount: float
    saved_amount: float = 0.0
