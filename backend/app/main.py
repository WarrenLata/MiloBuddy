import uvicorn
import vertexai
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

from .api import auth_router, chat_router, goals_router, transactions_router

# Initialize vertexai with the configured project (kept static here but can be
# moved to Settings if you want it configurable via .env)
vertexai.init(project=settings.gcloud_project_id)


app = FastAPI(title="Milo Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Milo backend is running"}


app.include_router(chat_router)
app.include_router(transactions_router)
app.include_router(goals_router)
app.include_router(auth_router)


if __name__ == "__main__":
    # Allow running the app directly: python -m app.main
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload and settings.debug,
    )
