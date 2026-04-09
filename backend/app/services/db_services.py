import calendar
from datetime import date, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def compute_freedom_score(user_id: str, db: AsyncSession) -> dict:
    today = date.today()
    month_start = today.replace(day=1)
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_remaining = days_in_month - today.day + 1

    total_budget = await db.scalar(
        text(
            "SELECT COALESCE(SUM(limit_amount_cents), 0) FROM budgets "
            "WHERE user_id = :uid AND month = :m AND year = :y"
        ),
        params={"uid": user_id, "m": today.month, "y": today.year},
    )

    spent = await db.scalar(
        text(
            "SELECT COALESCE(SUM(amount_cents), 0) FROM expenses "
            "WHERE user_id = :uid AND date >= :start AND date <= :today"
        ),
        params={"uid": user_id, "start": month_start, "today": today},
    )

    month_end = today.replace(day=days_in_month)
    committed = await db.scalar(
        text(
            "SELECT COALESCE(SUM(amount_cents), 0) FROM recurring_expenses "
            "WHERE user_id = :uid AND next_due_at <= :end AND is_active = true"
        ),
        params={"uid": user_id, "end": month_end},
    )

    # Ensure integers
    total_budget = int(total_budget or 0)
    spent = int(spent or 0)
    committed = int(committed or 0)

    safe_total = total_budget - spent - committed
    safe_today = safe_total // days_remaining if days_remaining > 0 else 0

    return {
        "safe_to_spend_today_cents": max(safe_today, 0),
        "safe_to_spend_total_cents": max(safe_total, 0),
        "budget_total_cents": total_budget,
        "spent_cents": spent,
        "committed_cents": committed,
        "days_remaining": days_remaining,
    }


async def check_ai_quota(user_row: Any, db: AsyncSession) -> bool:
    # user_row is expected to be a mapped User object or row with attributes
    # Reset counter if it's a new month
    now = datetime.utcnow()
    if (
        getattr(user_row, "ai_messages_reset_at", None) is None
        or getattr(user_row, "ai_messages_reset_at").month != now.month
    ):
        # perform DB update
        await db.execute(
            text(
                "UPDATE users SET ai_messages_used = 0, ai_messages_reset_at = now() WHERE id = :uid"
            ),
            {"uid": getattr(user_row, "id")},
        )
        await db.commit()

    if getattr(user_row, "plan", "free") == "plus":
        return True

    used = getattr(user_row, "ai_messages_used", 0) or 0
    return used < 20


async def get_goal_progress(goal_id: str, db: AsyncSession) -> int:
    val = await db.scalar(
        text(
            "SELECT COALESCE(SUM(amount_cents), 0) FROM goal_contributions WHERE goal_id = :gid"
        ),
        {"gid": goal_id},
    )
    return int(val or 0)
