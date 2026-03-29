from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login():
    return {"access_token": "<token>", "token_type": "bearer"}
