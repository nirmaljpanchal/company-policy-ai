from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.provider import AuthProvider, TokenPair
from app.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models.user import User


class LocalJWTProvider(AuthProvider):
    def authenticate(self, db: Session, email: str, password: str) -> User | None:
        stmt = select(User).where(User.email == email)
        user = db.scalar(stmt)

        if not user or not user.is_active:
            return None

        if not user.password_hash or not verify_password(password, user.password_hash):
            return None

        return user

    def issue_tokens(self, user: User) -> TokenPair:
        access_token = create_access_token(
            subject=str(user.id), role=user.role
        )
        refresh_token = create_refresh_token(subject=str(user.id))
        return TokenPair(access_token=access_token, refresh_token=refresh_token)

    def refresh(self, db: Session, refresh_token: str) -> TokenPair:
        claims = decode_token(refresh_token)

        if claims.get("type") != "refresh":
            raise ValueError("Token is not a valid refresh token")

        user_id = UUID(claims.get("sub"))
        user = db.get(User, user_id)

        if not user or not user.is_active:
            raise ValueError("User not found or is inactive")

        return self.issue_tokens(user)

    def identify(self, db: Session, access_token: str) -> User:
        claims = decode_token(access_token)

        if claims.get("type") != "access":
            raise ValueError("Token is not a valid access token")

        user_id = UUID(claims.get("sub"))
        user = db.get(User, user_id)

        if not user or not user.is_active:
            raise ValueError("User not found or is inactive")

        return user
