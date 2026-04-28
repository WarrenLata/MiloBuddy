import logging
import uuid
from collections.abc import AsyncIterator

from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.main_agent.tools.read_tools import (
    _get_categories,
    _get_category_budget,
    _get_context,
    _get_recent_expenses,
)
from app.agents.main_agent.tools.write_tools import (
    _create_budget,
    _create_category,
    _post_expense,
    _post_goal,
)
from app.core.config import settings
from app.db.engine import async_session
from app.db.models import Conversation

from .prompt import PROMPT

load_dotenv()
logging.basicConfig(level=logging.INFO)


logger = logging.getLogger(__name__)


async def save_user_message(user_id: str, session_id, query: str, db: AsyncSession):
    db.add(
        Conversation(
            user_id=user_id,
            session_id=session_id,
            role="user",
            content=query,
        )
    )
    await db.commit()


async def save_assistant_message(
    user_id: str, session_id: str, query: str, db: AsyncSession
):
    db.add(
        Conversation(
            user_id=user_id,
            session_id=session_id,
            role="assistant",
            content=query,
        )
    )
    await db.commit()


def create_agent(
    user_name: str | None = None,
    tools: list | None = None,
    description: str = "Main chat agent. Discuss with the user and decides which tools to use to answer the user's questions.",
) -> Agent:
    prompt = PROMPT.format(user_name=user_name or "utilisateur")

    return Agent(
        model=settings.adk_model,
        name="root_agent",
        description=description,
        instruction=prompt,
        tools=tools or [],
        generate_content_config=types.GenerateContentConfig(
            temperature=0.7,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )


def _extract_text_from_event(event: object) -> str | None:
    content = getattr(event, "content", None)
    parts = getattr(content, "parts", None) if content is not None else None
    if parts:
        texts: list[str] = []
        for part in parts:
            text = getattr(part, "text", None)
            if isinstance(text, str) and text:
                texts.append(text)
        if texts:
            return "".join(texts)

    delta = getattr(event, "delta", None)
    if delta is not None:
        text = getattr(delta, "text", None)
        if isinstance(text, str) and text:
            return text

    text = getattr(event, "text", None)
    if isinstance(text, str) and text:
        return text

    return None


class MainAgentRunner(Runner):
    """Custom Runner for the main agent.

    NOTE: initialization that requires awaiting (creating a session) is
    performed in the async factory `create` to avoid calling `asyncio.run`
    inside an already running event loop.
    """

    def __init__(
        self,
        user_id: str = "user",
        user_name: str | None = None,
    ):
        # Build the per-user agent instruction but don't perform async work here
        self.user = user_id
        self.agent = create_agent(user_name, tools=self._build_tools())
        # Initialize base Runner with an in-memory session service
        super().__init__(
            agent=self.agent,
            session_service=InMemorySessionService(),
            app_name="MAIN_CHAT",
        )

        # session will be set during the async factory
        self.session = None
        self.session_id = ""

        # Runner instance used to run the agent for this session
        self.runner = Runner(
            agent=self.agent,
            session_service=self.session_service,
            app_name="MAIN_CHAT",
        )

    # Dans __init__ — après self.user = user_id
    def _build_tools(self) -> list:
        user_id = self.user

        async def get_context() -> dict:
            """Retourne la situation financière complète de l'utilisateur.
            Appelle ce tool au début de chaque conversation et quand tu as
            besoin de données fraîches : Freedom Score, catégories disponibles,
            budgets du mois, objectifs actifs."""
            async with async_session() as db:
                return await _get_context(user_id, db)

        async def get_category_budget(category_name: str) -> dict:
            """Retourne le budget et les dépenses pour une catégorie spécifique.
            Appelle ce tool quand l'utilisateur demande combien il lui reste
            dans une catégorie précise.

            Args:
                category_name: Nom exact de la catégorie (ex: Alimentation, Transport)
            """
            async with async_session() as db:
                return await _get_category_budget(user_id, db, category_name)

        async def get_recent_expenses(limit: int = 5) -> dict:
            """Retourne les dernières dépenses de l'utilisateur.
            Appelle ce tool quand l'utilisateur veut voir son historique récent.

            Args:
                limit: Nombre de dépenses à retourner (défaut: 5)
            """
            async with async_session() as db:
                return await _get_recent_expenses(user_id, db, limit)

        async def post_expense(
            category_name: str, amount_cents: int, description: str
        ) -> dict:
            """Enregistre une dépense de l'utilisateur en base de données.
            Appelle ce tool dès que l'utilisateur mentionne qu'il a dépensé
            quelque chose. Choisis la catégorie la plus adaptée sans demander
            à l'utilisateur.

            Args:
                category_name: Catégorie depuis get_context() — la plus adaptée
                amount_cents: Montant en centimes. 45€ = 4500. 12,50€ = 1250.
                description: Ce que l'utilisateur a mentionné
            """
            async with async_session() as db:
                return await _post_expense(
                    user_id, db, category_name, amount_cents, description
                )

        async def create_budget(category_name: str, limit_amount_cents: int) -> dict:
            """Crée ou met à jour le budget mensuel d'une catégorie.
            Appelle ce tool quand l'utilisateur veut fixer ou modifier
            un budget pour une catégorie.

            Args:
                category_name: Catégorie depuis get_context()
                limit_amount_cents: Limite mensuelle en centimes. 500€ = 50000.
            """
            async with async_session() as db:
                return await _create_budget(
                    user_id, db, category_name, limit_amount_cents
                )

        async def create_category(name: str, icon: str | None = None) -> dict:
            """Crée une catégorie personnalisée pour l'utilisateur.
            Appelle ce tool uniquement si aucune catégorie existante
            ne correspond à la dépense de l'utilisateur.
            Demande toujours confirmation avant de créer.

            Args:
                name: Nom de la nouvelle catégorie (max 50 caractères)
                icon: Emoji représentatif optionnel (ex: 🎬, 🐶, 🎮)
            """
            async with async_session() as db:
                return await _create_category(user_id, db, name, icon)

        async def get_categories() -> dict:
            """Retourne toutes les catégories disponibles.
            Appelle ce tool quand l'utilisateur demande ses catégories
            ou avant de créer une nouvelle catégorie."""
            async with async_session() as db:
                return await _get_categories(user_id, db)

        async def post_goal(
            name: str, target_amount_cents: int, deadline: str | None = None
        ) -> dict:
            """Crée un objectif d'épargne pour l'utilisateur.
            Appelle ce tool quand l'utilisateur mentionne un projet
            ou un objectif financier.

            Args:
                name: Nom de l'objectif (ex: Vacances, Voiture, Téléphone)
                target_amount_cents: Montant cible en centimes. 1000€ = 100000.
                deadline: Date limite optionnelle format YYYY-MM-DD
            """
            async with async_session() as db:
                return await _post_goal(
                    user_id, db, name, target_amount_cents, deadline
                )

        return [
            get_context,
            get_category_budget,
            get_recent_expenses,
            post_expense,
            create_category,
            create_budget,
            post_goal,
        ]

    @classmethod
    async def create(cls, user_id: str = "user", user_name: str | None = None):
        """Async factory that constructs the runner and creates a session.

        This avoids calling asyncio.run inside the constructor and is safe to
        use from an existing event loop.
        """
        session_id = f"main_chat_{user_id}_{uuid.uuid4()}"

        instance = cls(user_id=user_id, user_name=user_name)

        # create_session is async so await it here
        instance.session = await instance.session_service.create_session(
            user_id=user_id, app_name="MAIN_CHAT", session_id=session_id
        )
        instance.session_id = session_id
        logger.info(f"Initialized MainAgentRunner with session_id: {session_id}")
        return instance

    async def stream_agent_text(
        self, query: str, user_name: str | None = None
    ) -> AsyncIterator[str]:
        content = types.Content(role="user", parts=[types.Part(text=query)])
        if async_session is None:
            raise RuntimeError("DB session not configured")

        async with async_session() as db:
            await save_user_message(
                user_id=self.user,
                session_id=self.session_id,
                query=query,
                db=db,
            )
        chunks = []
        seen_text = ""
        try:
            async for event in self.runner.run_async(
                user_id=self.user, session_id=self.session_id, new_message=content
            ):
                logger.info(f"Event type: {type(event)}")
                logger.info(
                    f"Event is_final: {event.is_final_response() if callable(getattr(event, 'is_final_response', None)) else 'N/A'}"
                )
                logger.info(f"Event content: {event.content}")
                is_final_fn = getattr(event, "is_final_response", None)
                is_final_response = is_final_fn() if callable(is_final_fn) else False

                text = _extract_text_from_event(event)
                if not text:
                    if is_final_response:
                        break
                    continue

                if text.startswith(seen_text):
                    delta = text[len(seen_text) :]
                    seen_text = text
                else:
                    delta = text
                    seen_text += text

                if delta:
                    chunks.append(delta)
                    yield delta

                if is_final_response:
                    full_response = "".join(chunks).strip()
                    if full_response and async_session is not None:
                        async with async_session() as db:
                            await save_assistant_message(
                                user_id=self.user,
                                session_id=self.session_id,
                                query=full_response,
                                db=db,
                            )
                    break
        except Exception as e:
            logger.error(f"Stream error for session {self.session_id}: {e}")
            yield "\n[Milo a rencontré une erreur. Réessaie dans un instant.]"

    async def call_agent_async(self, query: str, user_name: str | None = None) -> str:
        final_response_text = ""
        try:
            async for delta in self.stream_agent_text(query, user_name=user_name):
                final_response_text += delta
        except Exception as e:
            logger.error(
                f"Error occurred while calling agent: {e}! Session ID: {self.session_id}"
            )
            return f"Agent error: {e}"

        final_response_text = final_response_text.strip()
        if not final_response_text:
            return "No final text response captured."

        logger.info(f"==> Final Agent Response: {final_response_text}")
        return final_response_text
