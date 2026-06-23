from datetime import date
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Integer, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class QueryQuota(Base):
    __tablename__ = "query_quota"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    usage_date: Mapped[date] = mapped_column(Date, nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (PrimaryKeyConstraint("user_id", "usage_date"),)
