from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import chat_router, transactions_router, goals_router, auth_router


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
