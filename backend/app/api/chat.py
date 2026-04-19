import asyncio
import json
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.responses import StreamingResponse

from app.agents.main_agent.agent_adapter import handle_message, handle_message_stream
from app.core.auth import security, verify_firebase_token
from app.models.chat import ChatRequest

router = APIRouter(prefix="/chat", tags=["chat"], dependencies=[Security(security)])
logger = logging.getLogger(__name__)


@router.get("/ping")
async def ping():
    return {"status": "ok", "service": "chat"}


@router.post("/", dependencies=[Security(security)])
async def post_message(req: ChatRequest, user_id: str = Depends(verify_firebase_token)):
    """Forward a user message to the main agent and return its reply.

    If `user_name` is present it will be included in the message so the
    agent can address the user by name.
    """
    if req.stream:

        async def sse_event_stream():
            start = time.perf_counter()
            first_token_logged = False
            try:
                async for delta in handle_message_stream(
                    req.message, req.user_id, user_name=req.user_name
                ):
                    if not delta:
                        continue

                    if delta.startswith("Agent error:"):
                        payload = json.dumps(
                            {"error": delta.removeprefix("Agent error:").strip()},
                            ensure_ascii=False,
                        )
                        yield f"event: error\ndata: {payload}\n\n"
                        break

                    if not first_token_logged:
                        first_token_logged = True
                        logger.info(
                            "Chat stream first token user_id=%s in %.1fms",
                            req.user_id,
                            (time.perf_counter() - start) * 1000,
                        )

                    payload = json.dumps({"delta": delta}, ensure_ascii=False)
                    yield f"data: {payload}\n\n"
            except asyncio.CancelledError:
                logger.info("Chat stream client disconnected user_id=%s", req.user_id)
                return
            except Exception as e:
                logger.exception(
                    "Unhandled error in chat stream user_id=%s",
                    req.user_id,
                )
                payload = json.dumps({"error": str(e)}, ensure_ascii=False)
                yield f"event: error\ndata: {payload}\n\n"

            yield "event: done\ndata: {}\n\n"

        return StreamingResponse(
            sse_event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    try:
        reply = await handle_message(req.message, req.user_id, user_name=req.user_name)
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
