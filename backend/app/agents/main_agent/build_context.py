from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.services.db_services import compute_freedom_score


def onboarding_context() -> str:
    return """L'utilisateur débute sur Milo.\n
        Aucune donnée financière n'est encore configurée. Ta mission :
            - accueillir chaleureusement
            - poser une seule question utile à la fois
            - aider à configurer ses bases financières
            - ne pas submerger l’utilisateur
            - commencer simplement par budget ou objectif principal
            Tu peux l'aider à configurer ses catégories de dépenses, puis ses budgets, et enfin à enregistrer ses dépenses par exemple."""


async def build_main_agent_context(user_id: str, db: AsyncSession) -> str:
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        return onboarding_context()

    user_exists = await db.scalar(select(User.id).where(User.id == user_uuid).limit(1))
    if not user_exists:
        return onboarding_context()

    score = await compute_freedom_score(user_id=str(user_uuid), db=db)
    has_data = any(
        int(score.get(key, 0) or 0) > 0
        for key in ("spent_cents", "budget_total_cents", "committed_cents")
    )
    if not has_data:
        return onboarding_context()

    return (
        "Situation actuelle :\n"
        f"- Disponible aujourd'hui : {score['safe_to_spend_today_cents'] / 100:.2f} €\n"
        f"- Dépensé ce mois : {score['spent_cents'] / 100:.2f} €\n"
        f"- Budget total : {score['budget_total_cents'] / 100:.2f} €\n"
        f"- Charges fixes à venir : {score['committed_cents'] / 100:.2f} €\n"
        f"- Jours restants : {score['days_remaining']}\n"
        "\n"
    )
