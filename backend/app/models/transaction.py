from pydantic import BaseModel
from datetime import datetime


class Transaction(BaseModel):
    id: int
    amount: float
    currency: str
    timestamp: datetime
    description: str | None = None
