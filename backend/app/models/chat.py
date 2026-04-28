from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    user_name: str | None = None
    stream: bool = True
