from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(
    subject: str, role: str, extra_claims: Optional[Dict[str, Any]] = None
) -> str:
    settings = get_settings()
    now = datetime.utc.now()
    expires = now + timedelta(minutes=settings.access_token_ttl_min)

    claims = {
        "sub": subject,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": expires,
    }
    if extra_claims:
        claims.update(extra_claims)

    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_alg)


def create_refresh_token(subject: str) -> str:
    settings = get_settings()
    now = datetime.utc.now()
    expires = now + timedelta(days=settings.refresh_token_ttl_days)

    claims = {
        "sub": subject,
        "type": "refresh",
        "iat": now,
        "exp": expires,
    }

    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_alg)


def decode_token(token: str) -> Dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
        return payload
    except JWTError as e:
        if "expired" in str(e).lower():
            raise ValueError("Token has expired")
        raise ValueError(f"Invalid token: {str(e)}")
