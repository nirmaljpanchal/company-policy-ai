from abc import ABC, abstractmethod
from typing import NamedTuple, Optional

from sqlalchemy.orm import Session

from app.models.user import User


class TokenPair(NamedTuple):
    access_token: str
    refresh_token: str


class AuthProvider(ABC):
    @abstractmethod
    def authenticate(self, db: Session, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password. Return User if valid, None otherwise."""
        pass

    @abstractmethod
    def issue_tokens(self, user: User) -> TokenPair:
        """Issue access and refresh tokens for a user."""
        pass

    @abstractmethod
    def refresh(self, db: Session, refresh_token: str) -> TokenPair:
        """Validate refresh token and issue new token pair."""
        pass

    @abstractmethod
    def identify(self, db: Session, access_token: str) -> User:
        """Validate access token and return the associated user. Raise on invalid/expired token."""
        pass
