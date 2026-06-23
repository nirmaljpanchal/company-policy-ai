from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.deps import require_admin
from app.config import get_settings
from app.db import get_db
from app.models.user import User
from app.routers import admin, auth

app = FastAPI(
    title="PolicyChat API",
    description="RAG chatbot API for company policy questions",
    version="1.0.0",
)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict:
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


app.include_router(auth.router)
app.include_router(admin.router)

# Chat router to be added in later phases:
# from app.routers import chat
# app.include_router(chat.router, prefix="/chat", tags=["chat"])
