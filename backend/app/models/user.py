from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()"
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(String(50), default="employee", nullable=False)
    department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    azure_oid: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, nullable=False
    )
