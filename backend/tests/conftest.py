import os
from typing import Generator
import tempfile

import pytest

# Use a temporary file for SQLite to avoid threading issues with in-memory DB
test_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
test_db_path = test_db_file.name
test_db_file.close()

os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path}"
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("JWT_SECRET", "test-secret")

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import Base, SessionLocal, get_db, engine
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db() -> Generator[None, None, None]:
    """Clean up test database file after all tests."""
    yield
    try:
        os.remove(test_db_path)
    except Exception:
        pass


@pytest.fixture(scope="function", autouse=True)
def setup_db() -> Generator[None, None, None]:
    """Create all tables before each test, drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Get a database session for testing."""
    session = SessionLocal()
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
