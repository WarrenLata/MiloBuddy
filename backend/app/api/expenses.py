from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Security
from pydantic import BaseModel, Field
from sqlalchemy import extract, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import security, verify_firebase_token
from app.db.deps import get_db
from app.db.models import Category, Expense

router = APIRouter(
    prefix="/expenses", tags=["expenses"], dependencies=[Security(security)]
)


class CreateExpenseRequest(BaseModel):
    category_id: UUID
    amount_cents: int = Field(gt=0)
    description: str | None = None
    date: date
    input_method: Literal["manual", "voice", "ocr", "bank_sync"] = "manual"


class ExpenseOut(BaseModel):
    id: UUID
    category_id: UUID
    amount_cents: int
    description: str | None
    date: date
    input_method: str
    created_at: datetime


@router.post("", response_model=ExpenseOut, dependencies=[Security(security)])
async def create_expense(
    req: CreateExpenseRequest,
    user_id: str = Depends(verify_firebase_token),
    db: AsyncSession = Depends(get_db),
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

    expense = Expense(
        user_id=user_uuid,
        category_id=req.category_id,
        amount_cents=req.amount_cents,
        description=req.description,
        date=req.date,
        input_method=req.input_method,
    )
    db.add(expense)

    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    await db.refresh(expense)
    return ExpenseOut(
        id=expense.id,
        category_id=expense.category_id,
        amount_cents=expense.amount_cents,
        description=expense.description,
        date=expense.date,
        input_method=expense.input_method,
        created_at=expense.created_at,
    )


@router.get("", response_model=list[ExpenseOut], dependencies=[Security(security)])
async def list_expenses(
    month: int,
    year: int,
    user_id: str = Depends(verify_firebase_token),
    db: AsyncSession = Depends(get_db),
):
    user_uuid = UUID(user_id)
    result = await db.execute(
        select(Expense)
        .where(
            Expense.user_id == user_uuid,
            extract("month", Expense.date) == month,
            extract("year", Expense.date) == year,
        )
        .order_by(Expense.date.desc())
    )
    expenses = result.scalars().all()
    return [
        ExpenseOut(
            id=e.id,
            category_id=e.category_id,
            amount_cents=e.amount_cents,
            description=e.description,
            date=e.date,
            input_method=e.input_method,
            created_at=e.created_at,
        )
        for e in expenses
    ]
