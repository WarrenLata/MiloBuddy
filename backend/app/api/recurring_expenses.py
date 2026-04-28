from __future__ import annotations

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Security
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import security, verify_firebase_token
from app.db.deps import get_db
from app.db.models import Category, RecurringExpense

router = APIRouter(
    prefix="/recurring-expenses",
    tags=["recurring-expenses"],
    dependencies=[Security(security)],
)


class RecurringExpenseOut(BaseModel):
    id: UUID
    name: str
    amount_cents: int
    category_id: UUID
    category_name: str
    frequency: str
    day_of_month: int | None
    next_due_at: date
    is_active: bool


class CreateRecurringExpenseRequest(BaseModel):
    name: str
    category_id: UUID
    amount_cents: int = Field(gt=0)
    frequency: Literal["monthly", "weekly", "annual"]
    day_of_month: int | None = Field(default=None, ge=1, le=31)
    next_due_at: date


class DeleteRecurringExpenseOut(BaseModel):
    success: bool
    id: UUID


@router.get(
    "",
    response_model=list[RecurringExpenseOut],
    dependencies=[Security(security)],
)
async def list_recurring_expenses(
    user_id: Annotated[str, Depends(verify_firebase_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        user_uuid = UUID(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid user id") from exc

    result = await db.execute(
        select(RecurringExpense, Category.name)
        .join(Category, Category.id == RecurringExpense.category_id)
        .where(
            RecurringExpense.user_id == user_uuid,
            RecurringExpense.is_active.is_(True),
        )
        .order_by(RecurringExpense.next_due_at.asc())
    )

    rows = result.all()
    return [
        RecurringExpenseOut(
            id=re.id,
            name=re.name,
            amount_cents=re.amount_cents,
            category_id=re.category_id,
            category_name=category_name,
            frequency=re.frequency,
            day_of_month=re.day_of_month,
            next_due_at=re.next_due_at,
            is_active=re.is_active,
        )
        for re, category_name in rows
    ]


@router.post("", response_model=RecurringExpenseOut, dependencies=[Security(security)])
async def create_recurring_expense(
    req: CreateRecurringExpenseRequest,
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

    if req.frequency == "monthly" and req.day_of_month is None:
        raise HTTPException(
            status_code=400, detail="day_of_month is required for monthly frequency"
        )

    recurring = RecurringExpense(
        user_id=user_uuid,
        category_id=req.category_id,
        amount_cents=req.amount_cents,
        name=req.name,
        frequency=req.frequency,
        day_of_month=req.day_of_month,
        next_due_at=req.next_due_at,
        is_active=True,
    )
    db.add(recurring)

    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    await db.refresh(recurring)
    return RecurringExpenseOut(
        id=recurring.id,
        name=recurring.name,
        amount_cents=recurring.amount_cents,
        category_id=recurring.category_id,
        category_name=category.name,
        frequency=recurring.frequency,
        day_of_month=recurring.day_of_month,
        next_due_at=recurring.next_due_at,
        is_active=recurring.is_active,
    )


@router.delete(
    "/{recurring_expense_id}",
    response_model=DeleteRecurringExpenseOut,
    dependencies=[Security(security)],
)
async def delete_recurring_expense(
    recurring_expense_id: UUID,
    user_id: Annotated[str, Depends(verify_firebase_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        user_uuid = UUID(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid user id") from exc

    recurring_result = await db.execute(
        select(RecurringExpense)
        .where(RecurringExpense.id == recurring_expense_id)
        .limit(1)
    )
    recurring = recurring_result.scalars().first()
    if not recurring:
        raise HTTPException(status_code=404, detail="Recurring expense not found")

    if recurring.user_id != user_uuid:
        raise HTTPException(status_code=403, detail="Recurring expense not accessible")

    if not recurring.is_active:
        raise HTTPException(status_code=400, detail="Déjà désactivée")

    recurring.is_active = False

    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return DeleteRecurringExpenseOut(success=True, id=recurring.id)
