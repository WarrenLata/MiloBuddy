from contextlib import asynccontextmanager

import uvicorn
import vertexai
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import categories, goals, recurring_expenses
from app.core.auth import init_firebase
from app.core.config import settings

from .api import (
    auth_router,
    budgets_router,
    chat_router,
    expenses_router,
    freedom_score_router,
    transactions_router,
)

# Initialize vertexai with the configured project (kept static here but can be
# moved to Settings if you want it configurable via .env)
vertexai.init(project=settings.GOOGLE_CLOUD_PROJECT)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_firebase()
    yield


app = FastAPI(
    title="Milo Backend",
    lifespan=lifespan,
    swagger_ui_parameters={
        "persistAuthorization": True,
    },
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# def custom_openapi():
#     if app.openapi_schema:
#         return app.openapi_schema
#     schema = get_openapi(
#         title="Milo API",
#         version="1.0.0",
#         routes=app.routes,
#     )
#     schema["components"]["securitySchemes"] = {
#         "Bearer": {
#             "type": "http",
#             "scheme": "bearer",
#             "bearerFormat": "JWT",
#         }
#     }
#     schema["security"] = [{"Bearer": []}]
#     app.openapi_schema = schema
#     return schema

# app.openapi = custom_openapi


@app.get("/")
async def root():
    return {"message": "Milo backend is running"}


app.include_router(chat_router)
app.include_router(expenses_router)
app.include_router(budgets_router)
app.include_router(freedom_score_router)
app.include_router(transactions_router)
app.include_router(categories.router)
app.include_router(goals.router)
app.include_router(recurring_expenses.router)
app.include_router(auth_router)


if __name__ == "__main__":
    # Allow running the app directly: python -m app.main
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload and settings.debug,
    )
