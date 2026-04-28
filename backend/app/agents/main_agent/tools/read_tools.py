# app/agents/tools/read_tools.py
from __future__ import annotations

import calendar
from datetime import date
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Budget, Category, Expense, Goal, User
from app.services.db_services import compute_freedom_score


def _is_onboarding(score: dict) -> bool:
    return all(
        int(score.get(key, 0) or 0) == 0
        for key in ("spent_cents", "budget_total_cents", "committed_cents")
    )


async def _get_context(user_id: str, db: AsyncSession) -> dict:
    """Retourne la situation financière complète et à jour de l'utilisateur.
    Appelle ce tool au début de chaque conversation et quand tu as besoin
    de données fraîches. Contient : Freedom Score, catégories disponibles,
    budgets du mois, objectifs actifs.
    """
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        return {"onboarding": True, "message": "Utilisateur non trouvé."}

    user_exists = await db.scalar(select(User.id).where(User.id == user_uuid).limit(1))
    if not user_exists:
        return {"onboarding": True, "message": "Utilisateur non trouvé."}

    # Freedom Score
    score = await compute_freedom_score(user_id=str(user_uuid), db=db)

    if _is_onboarding(score):
        return {
            "onboarding": True,
            "message": "Aucune donnée financière configurée. Aide l'utilisateur à configurer ses budgets.",
        }

    # Catégories disponibles
    cats_result = await db.execute(
        select(Category)
        .where(or_(Category.user_id == user_uuid, Category.user_id.is_(None)))
        .order_by(Category.is_system.desc(), Category.name)
    )
    categories = [c.name for c in cats_result.scalars().all()]

    # Budgets du mois
    today = date.today()
    budgets_result = await db.execute(
        select(Budget, Category)
        .join(Category, Budget.category_id == Category.id)
        .where(
            Budget.user_id == user_uuid,
            Budget.month == today.month,
            Budget.year == today.year,
        )
    )
    budgets = [
        {
            "category": cat.name,
            "limit_euros": b.limit_amount_cents / 100,
        }
        for b, cat in budgets_result.all()
    ]

    # Goals actifs
    goals_result = await db.execute(
        select(Goal).where(
            Goal.user_id == user_uuid,
            Goal.is_active.is_(True),
        )
    )
    goals = [
        {
            "name": g.name,
            "target_euros": g.target_amount_cents / 100,
            "deadline": str(g.deadline) if g.deadline else None,
        }
        for g in goals_result.scalars().all()
    ]

    return {
        "onboarding": False,
        "freedom_score": {
            "safe_today_euros": score["safe_to_spend_today_cents"] / 100,
            "safe_total_euros": score["safe_to_spend_total_cents"] / 100,
            "spent_euros": score["spent_cents"] / 100,
            "budget_total_euros": score["budget_total_cents"] / 100,
            "committed_euros": score["committed_cents"] / 100,
            "days_remaining": score["days_remaining"],
        },
        "categories": categories,
        "budgets": budgets,
        "goals": goals,
    }


async def _get_category_budget(
    user_id: str, db: AsyncSession, category_name: str
) -> dict:
    """Retourne le budget et les dépenses pour une catégorie spécifique ce mois-ci.

    Args:
        category_name: Nom exact de la catégorie (ex: Alimentation, Transport)
    """
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        return {"error": "Utilisateur invalide"}

    today = date.today()

    # Trouve la catégorie
    cat_result = await db.execute(
        select(Category)
        .where(
            or_(Category.user_id == user_uuid, Category.user_id.is_(None)),
            Category.name == category_name,
        )
        .limit(1)
    )
    category = cat_result.scalars().first()
    if not category:
        return {"error": f"Catégorie '{category_name}' introuvable"}

    # Budget de la catégorie ce mois
    budget_result = await db.execute(
        select(Budget)
        .where(
            Budget.user_id == user_uuid,
            Budget.category_id == category.id,
            Budget.month == today.month,
            Budget.year == today.year,
        )
        .limit(1)
    )
    budget = budget_result.scalars().first()
    limit_cents = budget.limit_amount_cents if budget else 0

    # Dépensé dans cette catégorie ce mois
    spent_result = await db.execute(
        select(func.coalesce(func.sum(Expense.amount_cents), 0)).where(
            Expense.user_id == user_uuid,
            Expense.category_id == category.id,
            func.extract("month", Expense.date) == today.month,
            func.extract("year", Expense.date) == today.year,
        )
    )
    spent_cents = int(spent_result.scalar() or 0)
    remaining_cents = max(limit_cents - spent_cents, 0)

    return {
        "category": category_name,
        "limit_euros": limit_cents / 100,
        "spent_euros": spent_cents / 100,
        "remaining_euros": remaining_cents / 100,
        "days_remaining": (
            date(
                today.year, today.month, calendar.monthrange(today.year, today.month)[1]
            )
            - today
        ).days
        + 1,
        "has_budget": budget is not None,
    }


async def _get_recent_expenses(user_id: str, db: AsyncSession, limit: int = 5) -> dict:
    """Retourne les dernières dépenses de l'utilisateur.

    Args:
        limit: Nombre de dépenses à retourner (défaut: 5)
    """
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        return {"error": "Utilisateur invalide"}

    result = await db.execute(
        select(Expense, Category)
        .join(Category, Expense.category_id == Category.id)
        .where(Expense.user_id == user_uuid)
        .order_by(Expense.date.desc(), Expense.created_at.desc())
        .limit(limit)
    )
    expenses = [
        {
            "amount_euros": e.amount_cents / 100,
            "category": cat.name,
            "description": e.description,
            "date": str(e.date),
        }
        for e, cat in result.all()
    ]

    return {"expenses": expenses, "count": len(expenses)}


async def _get_categories(user_id: str, db: AsyncSession) -> dict:
    """Retourne toutes les catégories disponibles pour l'utilisateur.
    Système + personnalisées. Appelle ce tool quand l'utilisateur
    demande ses catégories ou avant de créer une catégorie.
    """
    result = await db.execute(
        select(Category)
        .where(or_(Category.user_id == UUID(user_id), Category.user_id.is_(None)))
        .order_by(Category.is_system.desc(), Category.name)
    )
    categories = result.scalars().all()
    return {
        "categories": [
            {
                "name": c.name,
                "icon": c.icon,
                "is_system": c.is_system,
            }
            for c in categories
        ]
    }
