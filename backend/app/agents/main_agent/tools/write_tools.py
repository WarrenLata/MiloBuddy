# app/agents/tools/write_tools.py
from __future__ import annotations

import logging
from datetime import date
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Budget, Category, Expense, Goal

logger = logging.getLogger(__name__)


async def _create_category(
    user_id: str,
    db: AsyncSession,
    name: str,
    icon: str | None = None,
) -> dict:
    """Crée une catégorie personnalisée pour l'utilisateur."""
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        return {"error": "Utilisateur invalide"}

    if not name or not name.strip():
        return {"error": "Le nom de la catégorie est requis"}

    cleaned_name = name.strip()
    if len(cleaned_name) > 50:
        return {"error": "Le nom doit faire 50 caractères max"}

    existing_result = await db.execute(
        select(Category)
        .where(
            or_(Category.user_id == user_uuid, Category.user_id.is_(None)),
            Category.name == cleaned_name,
        )
        .limit(1)
    )
    existing = existing_result.scalars().first()
    if existing:
        return {"error": "Une catégorie avec ce nom existe déjà"}

    category = Category(
        user_id=user_uuid,
        name=cleaned_name,
        icon=icon,
        color_hex=None,
        is_system=False,
    )
    db.add(category)

    try:
        await db.commit()
        await db.refresh(category)
    except Exception as exc:
        await db.rollback()
        logger.error(f"DB error in _create_category: {exc}")
        return {"error": "Erreur lors de la création. Réessaie."}

    return {
        "success": True,
        "id": str(category.id),
        "name": category.name,
        "icon": category.icon,
    }


async def _post_expense(
    user_id: str,
    db: AsyncSession,
    category_name: str,
    amount_cents: int,
    description: str,
) -> dict:
    """Enregistre une dépense pour l'utilisateur.

    Args:
        category_name: Catégorie exacte depuis la liste retournée par get_context.
            Choisis la plus adaptée — ne demande jamais à l'utilisateur.
        amount_cents: Montant en centimes. 45€ = 4500. 12,50€ = 1250.
        description: Ce que l'utilisateur a mentionné.
    """
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        return {"error": "Utilisateur invalide"}

    if amount_cents <= 0:
        return {"error": "Le montant doit être positif"}
    if not category_name or not category_name.strip():
        return {"error": "La catégorie est requise"}
    if not description or not description.strip():
        return {"error": "La description est requise"}

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
        return {
            "error": f"Catégorie '{category_name}' introuvable. "
            "Appelle get_context() pour obtenir la liste exacte."
        }
    try:

        expense = Expense(
            user_id=user_uuid,
            category_id=category.id,
            amount_cents=amount_cents,
            description=description,
            date=date.today(),
            input_method="manual",
        )
        db.add(expense)
        await db.commit()

        return {
            "success": True,
            "amount_euros": amount_cents / 100,
            "category": category_name,
            "description": description,
        }
    except ValueError as e:
        # deadline invalide, UUID invalide, etc.
        return {"error": f"Données invalides : {e}"}
    except Exception as e:
        await db.rollback()
        logger.error(f"DB error in post_expense: {e}")
        return {"error": "Erreur lors de l'enregistrement. Réessaie."}


async def _create_budget(
    user_id: str,
    db: AsyncSession,
    category_name: str,
    limit_amount_cents: int,
) -> dict:
    """Crée ou met à jour le budget mensuel d'une catégorie.

    Args:
        category_name: Catégorie depuis la liste de get_context.
        limit_amount_cents: Limite mensuelle en centimes. 500€ = 50000.
    """
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        return {"error": "Utilisateur invalide"}

    if limit_amount_cents <= 0:
        return {"error": "Le budget doit être positif"}

    today = date.today()

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

    if budget:
        budget.limit_amount_cents = limit_amount_cents
    else:

        budget = Budget(
            user_id=user_uuid,
            category_id=category.id,
            month=today.month,
            year=today.year,
            limit_amount_cents=limit_amount_cents,
        )
        db.add(budget)
    try:
        await db.commit()
    except ValueError as e:
        return {"error": f"Données invalides : {e}"}
    except Exception as e:
        await db.rollback()
        logger.error(f"DB error in _create_budget: {e}")
        return {"error": "Erreur lors de l'enregistrement. Réessaie."}

    return {
        "success": True,
        "category": category_name,
        "limit_euros": limit_amount_cents / 100,
        "month": today.month,
        "year": today.year,
    }


async def _post_goal(
    user_id: str,
    db: AsyncSession,
    name: str,
    target_amount_cents: int,
    deadline: str | None = None,
) -> dict:
    """Crée un objectif d'épargne.

    Args:
        name: Nom de l'objectif (ex: Vacances, Voiture, Téléphone)
        target_amount_cents: Montant cible en centimes. 1000€ = 100000.
        deadline: Date limite optionnelle format YYYY-MM-DD.
    """
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        return {"error": "Utilisateur invalide"}

    if target_amount_cents <= 0:
        return {"error": "Le montant cible doit être positif"}
    if not name or not name.strip():
        return {"error": "Le nom de l'objectif est requis"}
    try:

        goal = Goal(
            user_id=user_uuid,
            name=name,
            target_amount_cents=target_amount_cents,
            deadline=date.fromisoformat(deadline) if deadline else None,
            is_active=True,
        )
        db.add(goal)
        await db.commit()

        return {
            "success": True,
            "name": name,
            "target_euros": target_amount_cents / 100,
            "deadline": deadline,
        }
    except ValueError as e:
        # deadline invalide, UUID invalide, etc.
        return {"error": f"Données invalides : {e}"}
    except Exception as e:
        await db.rollback()
        logger.error(f"DB error in post_goal: {e}")
        return {"error": "Erreur lors de l'enregistrement. Réessaie."}
