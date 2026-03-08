from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://localhost/packvote"

    # Security
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Email
    SENDGRID_API_KEY: str = ""

    # AI providers
    HF_API_TOKEN: str = ""
    GROQ_API_KEY: str = ""

    # Unsplash
    UNSPLASH_ACCESS_KEY: str = ""

    # App
    FRONTEND_URL: str = "http://localhost:5173"
    ENVIRONMENT: str = "development"

    # AI model defaults
    DEFAULT_AI_MODEL: str = "Qwen/Qwen2.5-72B-Instruct"
    DEFAULT_AI_PROVIDER: str = "huggingface"


@lru_cache
def get_settings() -> Settings:
    return Settings()
