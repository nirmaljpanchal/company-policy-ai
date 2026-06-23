from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    """Output schema for a document."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    department: Optional[str] = None
    status: str
    uploaded_by: Optional[UUID] = None
    created_at: datetime


class DocumentListOut(BaseModel):
    """Output schema for a list of documents."""

    items: list[DocumentOut]
    total: int


class UploadResponse(BaseModel):
    """Response schema for successful document upload."""

    document: DocumentOut
    chunk_count: int
