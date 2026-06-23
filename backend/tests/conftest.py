import os
from typing import Generator
from uuid import UUID
import uuid

import pytest

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool
import sqlite3

from app.db import Base, get_db
from app.main import app

# Configure SQLite to handle UUIDs properly
def adapt_uuid(val):
    return str(val)

def convert_uuid(val):
    return uuid.UUID(val.decode())

sqlite3.register_adapter(UUID, adapt_uuid)
sqlite3.register_converter("uuid", convert_uuid)

# Create a test engine with in-memory SQLite configured for threading
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={
        "check_same_thread": False,
        "detect_types": sqlite3.PARSE_DECLTYPES,
    },
    poolclass=StaticPool,
)

Base.metadata.create_all(bind=test_engine)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Get a database session for testing."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db: Session) -> TestClient:
    """FastAPI test client with overridden db dependency."""
    def override_get_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
