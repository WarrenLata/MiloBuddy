import logging
import uuid

from dotenv import load_dotenv
from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .prompt import PROMPT

load_dotenv()
logging.basicConfig(level=logging.INFO)


logger = logging.getLogger(__name__)


def create_agent(
    user_name: str | None = None,
    description: str = "Main chat agent. Discuss with the user and decides which tools to use to answer the user's questions.",
) -> Agent:
    prompt = PROMPT.format(user_name=user_name or "utilisateur")

    return Agent(
        model="gemini-3-flash-preview",
        name="root_agent",
        description=description,
        instruction=prompt,
        tools=[],
    )


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
        self.agent = create_agent(user_name)
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

        # Prompt template already formatted in create if a user_name is provided
        # self.prompt = PROMPT.format(user_name=user_name)

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

    async def call_agent_async(self, query, user_name: str | None = None):
        # Build the text we send to the agent. Use the runner's `self.prompt`
        # (already formatted with the user_name in __init__) as a leading
        # instruction when present, then append the user-facing message. This
        # ensures the root agent receives the per-user prompt (including
        # greetings) even though the global `root_agent` instruction is static.

        content = types.Content(role="user", parts=[types.Part(text=query)])

        final_response_text = "No final text response captured."
        try:

            async for event in self.runner.run_async(
                user_id=self.user, session_id=self.session_id, new_message=content
            ):
                if event.is_final_response():
                    if (
                        event.content
                        and event.content.parts
                        and event.content.parts[0].text
                    ):
                        final_response_text = event.content.parts[0].text.strip()
                        logger.info(f"==> Final Agent Response: {final_response_text}")
                    else:
                        logger.warning(
                            f"==> Final Agent Response: [No text content in final event] : {event}! Session ID: {self.session_id}"
                        )
                        return final_response_text
        except Exception as e:
            logger.error(
                f"Error occurred while calling agent: {e}! Session ID: {self.session_id}"
            )

        return final_response_text
