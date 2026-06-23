from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    openai_api_key: str
    openai_chat_model: str = "gpt-4o-mini"
    openai_embed_model: str = "text-embedding-3-small"
    openai_moderation_model: str = "omni-moderation-latest"
    embed_dim: int = 1536
    jwt_secret: str
    jwt_alg: str = "HS256"
    access_token_ttl_min: int = 30
    refresh_token_ttl_days: int = 7
    daily_query_limit: int = 5
    auth_provider: str = "local"
    frontend_origin: str = "http://localhost:5173"

    # Azure Entra (optional, used when auth_provider="azure_entra")
    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_jwks_url: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
