from pydantic import BaseModel


class Goal(BaseModel):
    id: int
    title: str
    target_amount: float
    saved_amount: float = 0.0
