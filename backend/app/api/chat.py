from fastapi import APIRouter

router = APIRouter(prefix="/chat", tags=["chat"]) 


@router.get("/ping")
async def ping():
    return {"status": "ok", "service": "chat"}
