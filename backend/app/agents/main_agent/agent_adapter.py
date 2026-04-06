import asyncio
import logging
from typing import Dict

from .main_agent import MainAgentRunner

# Simple in-memory cache for MainAgentRunner instances keyed by user_id.
# This preserves the session (conversation memory) for each user across
# multiple HTTP requests. For production use consider eviction and persistence.
_runners: Dict[str, MainAgentRunner] = {}
_locks: Dict[str, asyncio.Lock] = {}

logger = logging.getLogger(__name__)


async def _get_or_create_runner(
    user_id: str, user_name: str | None = None
) -> MainAgentRunner:
    """Return a cached MainAgentRunner for user_id or create one if missing.

    Creation is done inside a thread because MainAgentRunner.__init__ uses
    `asyncio.run(...)` to create its session synchronously.
    """
    # fast path
    runner = _runners.get(user_id)
    if runner:
        return runner

    # ensure a lock exists for this user
    lock = _locks.get(user_id)
    if lock is None:
        lock = asyncio.Lock()
        _locks[user_id] = lock

    async with lock:
        # double-check after acquiring lock
        runner = _runners.get(user_id)
        if runner:
            return runner

        # Use the async factory to create the runner (avoids asyncio.run inside)
        runner = await MainAgentRunner.create(user_id=user_id, user_name=user_name)
        _runners[user_id] = runner
        logger.info(
            "Created MainAgentRunner for user_id=%s session_id=%s",
            user_id,
            (
                getattr(runner, "session_id", None)
                if getattr(runner, "session_id", None)
                else None
            ),
        )
        return runner


async def handle_message(
    message: str, user_id: str = "user", user_name: str | None = None
) -> str:
    """Forward a user message to the per-user MainAgentRunner and return the reply.

    This preserves conversation memory by reusing the same runner (and its
    session) for subsequent requests from the same `user_id`.
    """
    try:
        runner = await _get_or_create_runner(user_id, user_name)
        reply = await runner.call_agent_async(message, user_name=user_name)
        return reply
    except Exception as e:
        logger.exception(
            "Error while handling message with MainAgentRunner ! Message: %s, User ID: %s",
            message,
            user_id,
        )
        return f"Agent error: {e}"


def clear_runner(user_id: str) -> None:
    """Remove cached runner for a user (useful for tests or logout flows)."""
    runner = _runners.pop(user_id, None)
    _locks.pop(user_id, None)
    if runner:
        logger.info("Cleared MainAgentRunner for user_id=%s", user_id)
