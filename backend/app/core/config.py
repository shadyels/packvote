from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://localhost/packvote"

    # Security
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    RESET_TOKEN_EXPIRE_MINUTES: int = 60

    # Email
    BREVO_API_KEY: str = ""
    BREVO_FROM_EMAIL: str = "noreply@packvote.app"

    # AI providers
    CEREBRAS_API_KEY: str = ""

    # Unsplash
    UNSPLASH_ACCESS_KEY: str = ""

    # App
    FRONTEND_URL: str = "http://localhost:5173"
    ENVIRONMENT: str = "development"

    # AI model defaults
    DEFAULT_AI_MODEL: str = "gpt-oss-120b"
    # Reasoning effort for gpt-oss models. Escalate to "medium"/"high" via env
    # if prompt-adherence regressions are observed.
    DEFAULT_REASONING_EFFORT: Literal["low", "medium", "high"] = "low"


@lru_cache
def get_settings() -> Settings:
    return Settings()
