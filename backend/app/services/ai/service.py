import asyncio
import logging

from app.core.config import get_settings
from app.schemas.itinerary import AIGenerationResponse
from app.services.ai.base import AIProvider
from app.services.ai.groq import GroqProvider
from app.services.ai.huggingface import HuggingFaceProvider
from app.services.ai.json_utils import AIInputError

logger = logging.getLogger(__name__)

RETRY_DELAYS = [1.0, 2.0, 4.0]  # seconds between attempts on primary provider


class AIService:
    """Orchestrates AI provider selection, fallback, and retry logic.

    Provider selection order:
    1. Primary provider (HuggingFace by default) — 3 attempts with exponential backoff
    2. Fallback provider (Groq) if primary is exhausted — 1 attempt

    All calls are logged to ai_call_logs for monitoring.
    """

    def __init__(self, primary: AIProvider, fallback: AIProvider | None = None) -> None:
        self.primary = primary
        self.fallback = fallback

    @classmethod
    def from_settings(cls) -> "AIService":
        settings = get_settings()
        primary = HuggingFaceProvider(api_token=settings.HF_API_TOKEN)
        fallback: AIProvider | None = None
        if settings.GROQ_API_KEY:
            fallback = GroqProvider(api_key=settings.GROQ_API_KEY)
        return cls(primary=primary, fallback=fallback)

    async def generate_itineraries(
        self,
        prompt: str,
        num_options: int,
        model: str | None = None,
    ) -> tuple[AIGenerationResponse, str]:
        """Generate itineraries with retry on primary and fallback to Groq.

        Returns (response, provider_name).
        """
        settings = get_settings()
        resolved_model = model or settings.DEFAULT_AI_MODEL
        last_exc: Exception | None = None

        for attempt, delay in enumerate(RETRY_DELAYS):
            try:
                return await self.primary.generate_itineraries(
                    prompt, num_options, resolved_model
                )
            except AIInputError:
                # AI diagnosed the input as invalid — retrying won't help
                raise
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "HuggingFace attempt %d failed (%s): %s",
                    attempt + 1,
                    type(exc).__name__,
                    exc,
                )
                if attempt < len(RETRY_DELAYS) - 1:
                    await asyncio.sleep(delay)

        if self.fallback is not None:
            logger.info("Falling back to Groq provider")
            try:
                return await self.fallback.generate_itineraries(
                    prompt, num_options, resolved_model
                )
            except AIInputError:
                # AI diagnosed the input as invalid — no point trying other providers
                raise
            except Exception as exc:
                last_exc = exc
                logger.error(
                    "Groq fallback also failed (%s): %s", type(exc).__name__, exc
                )

        raise last_exc  # type: ignore[misc]

    async def generate_followup_survey(
        self,
        prompt: str,
        model: str | None = None,
    ) -> list[str]:
        settings = get_settings()
        resolved_model = model or settings.DEFAULT_AI_MODEL
        # TODO: implement with retry + fallback in iteration step
        return await self.primary.generate_followup_survey(prompt, resolved_model)
