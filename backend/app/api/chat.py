from fastapi import APIRouter, HTTPException

from app.agents.main_agent.agent_adapter import handle_message
from app.models.chat import ChatRequest

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/ping")
async def ping():
    return {"status": "ok", "service": "chat"}


@router.post("/")
async def post_message(req: ChatRequest):
    """Forward a user message to the main agent and return its reply.

    If `user_name` is present it will be included in the message so the
    agent can address the user by name.
    """
    try:
        reply = await handle_message(req.message, req.user_id, user_name=req.user_name)
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
