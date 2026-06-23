from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.quota import QueryQuota


@dataclass
class QuotaResult:
    allowed: bool
    count: int
    remaining: int
    limit: int


def check_and_increment(db: Session, user_id: UUID) -> QuotaResult:
    """Atomically check and increment daily quota. Returns QuotaResult."""
    settings = get_settings()
    limit = settings.daily_query_limit
    today = date.today()

    quota = db.query(QueryQuota).filter(
        QueryQuota.user_id == user_id,
        QueryQuota.usage_date == today
    ).first()

    if quota:
        quota.count += 1
        count = quota.count
    else:
        quota = QueryQuota(user_id=user_id, usage_date=today, count=1)
        db.add(quota)
        count = 1

    db.flush()

    if count > limit:
        db.rollback()
        return QuotaResult(
            allowed=False,
            count=count - 1,
            remaining=0,
            limit=limit
        )

    db.commit()
    return QuotaResult(
        allowed=True,
        count=count,
        remaining=limit - count,
        limit=limit
    )


def get_remaining(db: Session, user_id: UUID) -> int:
    """Get remaining quota for today without consuming it."""
    settings = get_settings()
    today = date.today()

    quota = db.query(QueryQuota).filter(
        QueryQuota.user_id == user_id,
        QueryQuota.usage_date == today
    ).first()

    count = quota.count if quota else 0
    return max(0, settings.daily_query_limit - count)
