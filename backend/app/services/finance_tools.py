import itertools
from datetime import datetime
from typing import Dict, List

from app.models.schemas import (
    GetBudgetResponse,
    GoalOut,
    PostExpenseRequest,
    PostGoalRequest,
    TrackBudgetRequest,
    TrackBudgetResponse,
    TransactionOut,
)

# Simple in-memory stores keyed by user_id
_transactions: Dict[str, List[TransactionOut]] = {}
_goals: Dict[str, List[GoalOut]] = {}
_budget_defaults: Dict[str, float] = {}

_tx_id_counter = itertools.count(1)
_goal_id_counter = itertools.count(1)


def _ensure_user(user_id: str):
    _transactions.setdefault(user_id, [])
    _goals.setdefault(user_id, [])
    _budget_defaults.setdefault(user_id, 2000.0)  # default monthly budget


def post_expense(user_id: str, req: PostExpenseRequest) -> TransactionOut:
    """Record an expense for the user (in-memory).

    Returns the created TransactionOut.
    """
    _ensure_user(user_id)
    tx = TransactionOut(
        id=next(_tx_id_counter),
        amount=req.amount,
        currency=req.currency,
        timestamp=datetime.utcnow(),
        description=req.description,
    )
    _transactions[user_id].append(tx)
    return tx


def get_budget(user_id: str) -> GetBudgetResponse:
    _ensure_user(user_id)
    monthly = _budget_defaults[user_id]
    txs = _transactions[user_id]
    total_spent = sum(t.amount for t in txs)
    remaining = monthly - total_spent
    return GetBudgetResponse(
        monthly_budget=monthly,
        total_spent=round(total_spent, 2),
        remaining=round(remaining, 2),
        transactions=txs,
    )


def track_budget(user_id: str, req: TrackBudgetRequest) -> TrackBudgetResponse:
    _ensure_user(user_id)
    budget = _budget_defaults[user_id]
    spent = sum(t.amount for t in _transactions[user_id])
    remaining = budget - spent
    allowed = req.amount <= remaining
    remaining_if_allowed = round(remaining - req.amount if allowed else remaining, 2)
    return TrackBudgetResponse(
        allowed=allowed, remaining_if_allowed=remaining_if_allowed
    )


def post_goal(user_id: str, req: PostGoalRequest) -> GoalOut:
    _ensure_user(user_id)
    goal = GoalOut(
        id=next(_goal_id_counter),
        title=req.title,
        target_amount=req.target_amount,
        saved_amount=0.0,
    )
    _goals[user_id].append(goal)
    return goal
