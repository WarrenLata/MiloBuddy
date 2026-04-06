from datetime import datetime

from pydantic import BaseModel


class Transaction(BaseModel):
    id: int
    amount: float
    currency: str
    timestamp: datetime
    description: str | None = None
