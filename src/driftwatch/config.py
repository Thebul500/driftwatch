"""Application configuration from environment variables."""

import secrets

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    database_url: str = "postgresql+asyncpg://localhost:5432/driftwatch"
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    access_token_expire_minutes: int = 30
    debug: bool = False

    model_config = {"env_prefix": "DRIFTWATCH_"}


settings = Settings()
