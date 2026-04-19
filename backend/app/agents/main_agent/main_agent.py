import logging
import uuid
from collections.abc import AsyncIterator

from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.core.config import settings
from app.db.engine import async_session

from .build_context import build_main_agent_context, onboarding_context
from .prompt import PROMPT

load_dotenv()
logging.basicConfig(level=logging.INFO)


logger = logging.getLogger(__name__)


def create_agent(
    user_name: str | None = None,
    build_context: str = "",
    description: str = "Main chat agent. Discuss with the user and decides which tools to use to answer the user's questions.",
) -> Agent:
    prompt = PROMPT.format(
        user_name=user_name or "utilisateur",
        build_context=build_context,
    )

    return Agent(
        model=settings.adk_model,
        name="root_agent",
        description=description,
        instruction=prompt,
        tools=[],
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
        build_context: str = "",
    ):
        # Build the per-user agent instruction but don't perform async work here
        self.agent = create_agent(user_name, build_context=build_context)
        # Initialize base Runner with an in-memory session service
        super().__init__(
            agent=self.agent,
            session_service=InMemorySessionService(),
            app_name="MAIN_CHAT",
        )

        self.user = user_id
        # session will be set during the async factory
        self.session = None
        self.session_id = ""

        # Runner instance used to run the agent for this session
        self.runner = Runner(
            agent=self.agent,
            session_service=self.session_service,
            app_name="MAIN_CHAT",
        )

    @classmethod
    async def create(cls, user_id: str = "user", user_name: str | None = None):
        """Async factory that constructs the runner and creates a session.

        This avoids calling asyncio.run inside the constructor and is safe to
        use from an existing event loop.
        """
        session_id = f"main_chat_{user_id}_{uuid.uuid4()}"
        build_context = onboarding_context()
        if async_session is not None:
            try:
                async with async_session() as db:
                    build_context = await build_main_agent_context(user_id, db=db)
            except Exception:
                logger.exception(
                    "Failed to build main agent context; falling back to onboarding context. user_id=%s",
                    user_id,
                )
                build_context = onboarding_context()

        instance = cls(
            user_id=user_id,
            user_name=user_name,
            build_context=build_context,
        )

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
                    yield delta

                if is_final_response:
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
