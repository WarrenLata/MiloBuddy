import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Dict

from .main_agent import MainAgentRunner

# Simple in-memory cache for MainAgentRunner instances keyed by user_id.
# This preserves the session (conversation memory) for each user across
# multiple HTTP requests. For production use consider eviction and persistence.
_runners: Dict[str, MainAgentRunner] = {}
_locks: Dict[str, asyncio.Lock] = {}

logger = logging.getLogger(__name__)


def _get_lock(user_id: str) -> asyncio.Lock:
    lock = _locks.get(user_id)
    if lock is None:
        lock = asyncio.Lock()
        _locks[user_id] = lock
    return lock


async def _get_or_create_runner_locked(
    user_id: str, user_name: str | None = None
) -> MainAgentRunner:
    runner = _runners.get(user_id)
    if runner:
        return runner

    runner = await MainAgentRunner.create(user_id=user_id, user_name=user_name)
    _runners[user_id] = runner
    logger.info(
        "Created MainAgentRunner for user_id=%s session_id=%s",
        user_id,
        getattr(runner, "session_id", None),
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
        lock = _get_lock(user_id)
        async with lock:
            runner = await _get_or_create_runner_locked(user_id, user_name)
            return await runner.call_agent_async(message, user_name=user_name)
    except Exception as e:
        logger.exception(
            "Error while handling with MainAgentRunner. message=%s user_id=%s",
            message,
            user_id,
        )
        return f"Agent error: {e}"


async def handle_message_stream(
    message: str, user_id: str = "user", user_name: str | None = None
) -> AsyncIterator[str]:
    """Stream a user message to the per-user MainAgentRunner and yield deltas."""
    lock = _get_lock(user_id)
    async with lock:
        runner = await _get_or_create_runner_locked(user_id, user_name)
        try:
            async for delta in runner.stream_agent_text(message, user_name=user_name):
                yield delta
        except Exception as e:
            logger.exception(
                "Error while streaming with MainAgentRunner. message=%s user_id=%s",
                message,
                user_id,
            )
            yield f"Agent error: {e}"


def clear_runner(user_id: str) -> None:
    """Remove cached runner for a user (useful for tests or logout flows)."""
    runner = _runners.pop(user_id, None)
    _locks.pop(user_id, None)
    if runner:
        logger.info("Cleared MainAgentRunner for user_id=%s", user_id)
