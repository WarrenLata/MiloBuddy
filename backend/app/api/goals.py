from fastapi import APIRouter

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("/")
async def list_goals():
    return {"goals": []}
