from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated settings for the AgentShield control API."""

    app_name: str = "AgentShield Ops API"
    app_version: str = "0.1.0"
    environment: str = "development"
    api_prefix: str = "/api/v1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return one cached settings object per application process."""

    return Settings()