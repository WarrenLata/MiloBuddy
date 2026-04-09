from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import verify_firebase_token
from app.db.deps import get_db
from app.models import schemas
from app.services.finance_tools import get_budget, post_expense

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.post("/", response_model=schemas.TransactionOut)
async def create_expense(
    req: schemas.PostExpenseRequest,
    user_id: str = Depends(verify_firebase_token),
    db: AsyncSession = Depends(get_db),
):
    tx = post_expense(user_id, req)
    return tx


@router.get("/", response_model=schemas.GetBudgetResponse)
async def list_expenses(
    month: Optional[int] = None,
    year: Optional[int] = None,
    user_id: str = Depends(verify_firebase_token),
    db: AsyncSession = Depends(get_db),
):
    # For simplicity return budget summary placeholder backed by in-memory store
    return get_budget(user_id)
