from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_by: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="ready", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, nullable=False
    )
