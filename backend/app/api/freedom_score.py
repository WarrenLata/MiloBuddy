from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Security
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import security, verify_firebase_token
from app.db.deps import get_db
from app.services.db_services import compute_freedom_score

bearer_scheme = HTTPBearer()

router = APIRouter(tags=["freedom-score"], dependencies=[Security(security)])


class FreedomScoreOut(BaseModel):
    safe_to_spend_today_cents: int
    spent_cents: int
    budget_total_cents: int
    committed_cents: int
    days_remaining: int


@router.get(
    "/freedom-score", response_model=FreedomScoreOut, dependencies=[Security(security)]
)
async def get_freedom_score(
    user_id: Annotated[str, Depends(verify_firebase_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    score = await compute_freedom_score(user_id=user_id, db=db)
    return FreedomScoreOut(
        safe_to_spend_today_cents=score["safe_to_spend_today_cents"],
        spent_cents=score["spent_cents"],
        budget_total_cents=score["budget_total_cents"],
        committed_cents=score["committed_cents"],
        days_remaining=score["days_remaining"],
    )
