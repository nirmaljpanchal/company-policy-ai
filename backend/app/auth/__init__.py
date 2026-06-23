from app.auth.local_jwt import LocalJWTProvider
from app.auth.provider import AuthProvider, TokenPair
from app.config import get_settings


def get_auth_provider() -> AuthProvider:
    settings = get_settings()
    if settings.auth_provider == "local":
        return LocalJWTProvider()
    elif settings.auth_provider == "azure_entra":
        raise NotImplementedError("Azure Entra authentication is not yet implemented")
    else:
        raise ValueError(f"Unknown auth provider: {settings.auth_provider}")


__all__ = ["get_auth_provider", "AuthProvider", "TokenPair"]
