from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=5000)
    chat_history: Optional[list[dict]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    quota_remaining: int
    blocked: bool = False
    block_reason: Optional[str] = None
