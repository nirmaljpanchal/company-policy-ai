from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.orm import Session

from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    poolclass=None,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
