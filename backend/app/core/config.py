from functools import lru_cache
from typing import Any, Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_SECRET = "change-me-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://localhost/packvote"

    # Security
    SECRET_KEY: str = _DEFAULT_SECRET
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
    # gemini-2.5-flash was retired for new API keys (404 "no longer available
    # to new users") — confirmed against both a fresh key and production's
    # Railway key. gemini-3.6-flash is the current Flash model.
    DEFAULT_AI_MODEL: str = "gemini-3.6-flash"
    # "none" omits reasoning_effort entirely and lets AI_EXTRA_BODY govern the
    # thinking pass — required for Gemini, which rejects reasoning_effort and
    # thinking_config together. Escalate via env if prompt adherence regresses.
    DEFAULT_REASONING_EFFORT: Literal["none", "low", "medium", "high"] = "none"
    # Vendor-specific request knobs the OpenAI schema has no field for, merged
    # into the request as `extra_body`. Set from env as JSON.
    #
    # Gemini draws thinking tokens from the SAME max_tokens budget as the
    # response, so an enabled thinking pass risks silently truncating the
    # itinerary JSON. Gemini 3.x replaced thinking_budget with the string enum
    # thinking_level (minimal/low/medium/high, default "medium" on 3.6 Flash);
    # sending thinking_budget on a 3.x model 400s. "minimal" is the lowest
    # level Flash models support — per Google's docs it approximates but does
    # NOT guarantee zero thinking tokens, unlike thinking_budget=0 on 2.5. If
    # `finish_reason=length` warnings start appearing (see openai_compat.py),
    # that is this non-guarantee manifesting. Set to {} for providers that
    # reject unknown request fields.
    #
    # Double-nested on purpose: the OpenAI SDK's extra_body= kwarg merges its
    # keys into the TOP LEVEL of the outgoing request body, but Gemini's
    # OpenAI-compat endpoint expects a literal `extra_body` field there (it's
    # a real field in their request proto). A single-level {"google": ...}
    # produces `400 Unknown name "google"`.
    AI_EXTRA_BODY: dict[str, Any] = {
        "extra_body": {"google": {"thinking_config": {"thinking_level": "minimal"}}}
    }

    @model_validator(mode="after")
    def _reject_default_secret(self) -> "Settings":
        if self.ENVIRONMENT != "development" and self.SECRET_KEY == _DEFAULT_SECRET:
            raise ValueError(
                "SECRET_KEY must be set when ENVIRONMENT is not development"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
