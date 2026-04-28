from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Security
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import security, verify_firebase_token
from app.db.deps import get_db
from app.db.models import Expense, Goal, GoalContribution

router = APIRouter(prefix="/goals", tags=["goals"], dependencies=[Security(security)])


class GoalOut(BaseModel):
    id: UUID
    name: str
    target_amount_cents: int
    progress_cents: int
    progress_percent: float
    deadline: date | None
    is_active: bool
    created_at: datetime


class CreateGoalContributionRequest(BaseModel):
    amount_cents: int = Field(gt=0)
    source: Literal["manual", "auto"]
    expense_id: UUID | None = None


class GoalContributionOut(BaseModel):
    id: UUID
    goal_id: UUID
    amount_cents: int
    source: str
    created_at: datetime


@router.get("", response_model=list[GoalOut], dependencies=[Security(security)])
async def list_goals(
    user_id: Annotated[str, Depends(verify_firebase_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        user_uuid = UUID(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid user id") from exc

    progress_cents_col = func.coalesce(
        func.sum(GoalContribution.amount_cents), 0
    ).label("progress_cents")

    result = await db.execute(
        select(Goal, progress_cents_col)
        .outerjoin(
            GoalContribution,
            and_(
                GoalContribution.goal_id == Goal.id,
                GoalContribution.user_id == user_uuid,
            ),
        )
        .where(Goal.user_id == user_uuid, Goal.is_active.is_(True))
        .group_by(Goal.id)
    )

    rows = result.all()
    out: list[GoalOut] = []
    for goal, progress_cents in rows:
        target = goal.target_amount_cents or 0
        percent = 0.0
        if target > 0:
            percent = min((float(progress_cents) / float(target)) * 100.0, 100.0)

        out.append(
            GoalOut(
                id=goal.id,
                name=goal.name,
                target_amount_cents=goal.target_amount_cents,
                progress_cents=int(progress_cents or 0),
                progress_percent=percent,
                deadline=goal.deadline,
                is_active=goal.is_active,
                created_at=goal.created_at,
            )
        )
    return out


@router.post(
    "/{goal_id}/contributions",
    response_model=GoalContributionOut,
    dependencies=[Security(security)],
)
async def create_goal_contribution(
    goal_id: UUID,
    req: CreateGoalContributionRequest,
    user_id: Annotated[str, Depends(verify_firebase_token)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        user_uuid = UUID(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid user id") from exc

    goal_result = await db.execute(select(Goal).where(Goal.id == goal_id).limit(1))
    goal = goal_result.scalars().first()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    if goal.user_id != user_uuid:
        raise HTTPException(status_code=403, detail="Goal not accessible")

    if not goal.is_active:
        raise HTTPException(status_code=400, detail="Goal is not active")

    if req.expense_id is not None:
        expense_result = await db.execute(
            select(Expense).where(Expense.id == req.expense_id).limit(1)
        )
        expense = expense_result.scalars().first()
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")
        if expense.user_id != user_uuid:
            raise HTTPException(status_code=403, detail="Expense not accessible")

    contribution = GoalContribution(
        user_id=user_uuid,
        goal_id=goal_id,
        amount_cents=req.amount_cents,
        source=req.source,
        expense_id=req.expense_id,
    )
    db.add(contribution)

    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    await db.refresh(contribution)
    return GoalContributionOut(
        id=contribution.id,
        goal_id=contribution.goal_id,
        amount_cents=contribution.amount_cents,
        source=contribution.source,
        created_at=contribution.created_at,
    )
