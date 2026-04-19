from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Security
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import security, verify_firebase_token
from app.db.deps import get_db
from app.db.models import Budget, Category

router = APIRouter(
    prefix="/budgets", tags=["budgets"], dependencies=[Security(security)]
)


class UpsertBudgetRequest(BaseModel):
    category_id: UUID
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2024)
    limit_amount_cents: int = Field(gt=0)


class BudgetOut(BaseModel):
    id: UUID
    category_id: UUID
    month: int
    year: int
    limit_amount_cents: int


@router.post("", response_model=BudgetOut, dependencies=[Security(security)])
async def upsert_budget(
    req: UpsertBudgetRequest,
    user_id: Annotated[str, Depends(verify_firebase_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        user_uuid = UUID(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid user id") from exc

    category_result = await db.execute(
        select(Category).where(Category.id == req.category_id).limit(1)
    )
    category = category_result.scalars().first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if category.user_id is not None and category.user_id != user_uuid:
        raise HTTPException(status_code=403, detail="Category not accessible")

    budget_result = await db.execute(
        select(Budget)
        .where(
            Budget.user_id == user_uuid,
            Budget.category_id == req.category_id,
            Budget.month == req.month,
            Budget.year == req.year,
        )
        .limit(1)
    )
    budget = budget_result.scalars().first()
    if budget:
        budget.limit_amount_cents = req.limit_amount_cents
    else:
        budget = Budget(
            user_id=user_uuid,
            category_id=req.category_id,
            month=req.month,
            year=req.year,
            limit_amount_cents=req.limit_amount_cents,
        )
        db.add(budget)

    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    await db.refresh(budget)
    return BudgetOut(
        id=budget.id,
        category_id=budget.category_id,
        month=budget.month,
        year=budget.year,
        limit_amount_cents=budget.limit_amount_cents,
    )


@router.get("", response_model=list[BudgetOut], dependencies=[Security(security)])
async def list_budgets(
    month: int,
    year: int,
    user_id: Annotated[str, Depends(verify_firebase_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    user_uuid = UUID(user_id)
    result = await db.execute(
        select(Budget).where(
            Budget.user_id == user_uuid,
            Budget.month == month,
            Budget.year == year,
        )
    )
    budgets = result.scalars().all()
    return [
        BudgetOut(
            id=b.id,
            category_id=b.category_id,
            month=b.month,
            year=b.year,
            limit_amount_cents=b.limit_amount_cents,
        )
        for b in budgets
    ]
