from functools import lru_cache
from typing import Any, Literal

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

    # AI provider — any OpenAI-compatible chat-completions endpoint.
    # Defaults target Google Gemini's free tier. Switching provider means changing
    # these three plus DEFAULT_AI_MODEL and AI_EXTRA_BODY below; no code change,
    # but re-tune the ceilings in services/ai/rate_limiter.py to match.
    AI_API_KEY: str = ""
    AI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    # Recorded in ai_call_logs.provider and itineraries.provider.
    AI_PROVIDER_NAME: str = "gemini"

    # Unsplash
    UNSPLASH_ACCESS_KEY: str = ""

    # App
    FRONTEND_URL: str = "http://localhost:5173"
    ENVIRONMENT: str = "development"

    # AI model defaults
    DEFAULT_AI_MODEL: str = "gemini-2.5-flash"
    # "none" omits reasoning_effort entirely and lets AI_EXTRA_BODY govern the
    # thinking pass — required for Gemini, which rejects reasoning_effort and
    # thinking_config together. Escalate via env if prompt adherence regresses.
    DEFAULT_REASONING_EFFORT: Literal["none", "low", "medium", "high"] = "none"
    # Vendor-specific request knobs the OpenAI schema has no field for, merged
    # into the request as `extra_body`. Set from env as JSON.
    #
    # Gemini draws thinking tokens from the SAME max_tokens budget as the
    # response, so an enabled thinking pass silently truncates the itinerary
    # JSON. thinking_budget=0 disables it on Gemini 2.5. Gemini 3.x uses
    # {"thinking_level": "low"} instead. Set to {} for providers that reject
    # unknown fields.
    AI_EXTRA_BODY: dict[str, Any] = {
        "google": {"thinking_config": {"thinking_budget": 0}}
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
