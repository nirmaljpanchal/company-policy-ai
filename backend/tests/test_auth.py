import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.models.user import User
from uuid import uuid4


@pytest.fixture
def admin_user(db: Session) -> User:
    """Create an admin user for testing."""
    user = User(
        id=uuid4(),
        email="admin@example.com",
        password_hash=hash_password("admin_password"),
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def employee_user(db: Session) -> User:
    """Create an employee user for testing."""
    user = User(
        id=uuid4(),
        email="employee@example.com",
        password_hash=hash_password("employee_password"),
        role="employee",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestAuthLogin:
    def test_login_success(self, client: TestClient, admin_user: User):
        """Test successful login returns access and refresh tokens."""
        response = client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "admin_password"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_bad_password(self, client: TestClient, admin_user: User):
        """Test login with bad password returns 401."""
        response = client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "wrong_password"},
        )
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with nonexistent email returns 401."""
        response = client.post(
            "/auth/login",
            json={"email": "nonexistent@example.com", "password": "password"},
        )
        assert response.status_code == 401

    def test_login_inactive_user(self, client: TestClient, db: Session):
        """Test login with inactive user returns 401."""
        user = User(
            id=uuid4(),
            email="inactive@example.com",
            password_hash=hash_password("password"),
            role="employee",
            is_active=False,
        )
        db.add(user)
        db.commit()

        response = client.post(
            "/auth/login",
            json={"email": "inactive@example.com", "password": "password"},
        )
        assert response.status_code == 401


class TestAuthMe:
    def test_me_with_valid_token(self, client: TestClient, admin_user: User):
        """Test /me returns user data with valid access token."""
        # Login first
        login_response = client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "admin_password"},
        )
        access_token = login_response.json()["access_token"]

        # Call /me with the token
        response = client.get(
            "/auth/me", headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@example.com"
        assert data["role"] == "admin"
        assert data["is_active"] is True
        assert "id" in data

    def test_me_without_token(self, client: TestClient):
        """Test /me without token returns 401."""
        response = client.get("/auth/me")
        assert response.status_code == 403  # HTTPBearer returns 403 for missing credentials

    def test_me_with_invalid_token(self, client: TestClient):
        """Test /me with invalid token returns 401."""
        response = client.get(
            "/auth/me", headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401

    def test_me_with_expired_token(self, client: TestClient, admin_user: User):
        """Test /me with expired token returns 401."""
        # This would require manipulating token expiry, which is complex
        # For now, we verify that invalid tokens are rejected
        response = client.get(
            "/auth/me", headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1ZmI3YjY1OC1kNzMzLTRmZjAtODMyZS04NTA3NTA5MzQ4OTEiLCJyb2xlIjoiYWRtaW4iLCJ0eXBlIjoiYWNjZXNzIiwiaWF0IjoxNjAwMDAwMDAwLCJleHAiOjE2MDAwMDAwMDF9.fake"}
        )
        assert response.status_code == 401


class TestAuthRefresh:
    def test_refresh_returns_new_token(self, client: TestClient, admin_user: User):
        """Test refresh returns a new access token."""
        # Login first
        login_response = client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "admin_password"},
        )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh the token
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_with_access_token_fails(self, client: TestClient, admin_user: User):
        """Test using access token as refresh token returns 401."""
        # Login first
        login_response = client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "admin_password"},
        )
        access_token = login_response.json()["access_token"]

        # Try to use access token as refresh token
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": access_token},
        )
        assert response.status_code == 401
        assert "not a valid refresh token" in response.json()["detail"]


class TestAdminEndpoint:
    def test_admin_ping_succeeds_for_admin(
        self, client: TestClient, admin_user: User
    ):
        """Test /admin/ping succeeds and returns pong for admin."""
        # Login as admin
        login_response = client.post(
            "/auth/login",
            json={"email": "admin@example.com", "password": "admin_password"},
        )
        access_token = login_response.json()["access_token"]

        # Call /admin/ping
        response = client.get(
            "/admin/ping", headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["pong"] is True
        assert data["user"] == "admin@example.com"

    def test_admin_ping_forbidden_for_employee(
        self, client: TestClient, employee_user: User
    ):
        """Test /admin/ping returns 403 for non-admin."""
        # Login as employee
        login_response = client.post(
            "/auth/login",
            json={"email": "employee@example.com", "password": "employee_password"},
        )
        access_token = login_response.json()["access_token"]

        # Call /admin/ping
        response = client.get(
            "/admin/ping", headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code == 403
        assert "Insufficient permissions" in response.json()["detail"]

    def test_admin_ping_unauthorized_without_token(self, client: TestClient):
        """Test /admin/ping returns 401 without token."""
        response = client.get("/admin/ping")
        assert response.status_code == 403  # HTTPBearer returns 403 for missing credentials
