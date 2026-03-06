"""Application configuration from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    database_url: str = "postgresql+asyncpg://localhost:5432/driftwatch"
    secret_key: str  # Required — set DRIFTWATCH_SECRET_KEY
    access_token_expire_minutes: int = 30
    debug: bool = False

    model_config = {"env_prefix": "DRIFTWATCH_"}


settings = Settings()
