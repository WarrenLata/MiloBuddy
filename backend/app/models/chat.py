from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str
    user_id: str = "user"
    user_name: str | None = None