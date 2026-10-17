import asyncio
import logging

from openai import RateLimitError

from app.core.config import get_settings
from app.models.ai_call_log import AICallLog
from app.schemas.itinerary import AIGenerationResponse
from app.services.ai.json_utils import AIInputError
from app.services.ai.openai_compat import OpenAICompatProvider
from app.services.ai.rate_limiter import LocalRateLimitError

logger = logging.getLogger(__name__)

RETRY_DELAYS = [1.0, 2.0, 4.0]  # seconds between attempts — transient errors
RATE_LIMIT_DELAYS = [30.0, 60.0, 90.0]  # seconds between attempts — HTTP 429


class AIService:
    """Orchestrates AI provider selection and retry logic.

    Retries the configured provider up to 3 times with exponential backoff.
    On total exhaustion re-raises the last exception.
    """

    def __init__(self, provider: OpenAICompatProvider) -> None:
        self.provider = provider

    @classmethod
    def from_settings(cls) -> "AIService":
        settings = get_settings()
        return cls(
            provider=OpenAICompatProvider(
                api_key=settings.AI_API_KEY,
                base_url=settings.AI_BASE_URL,
                provider_name=settings.AI_PROVIDER_NAME,
                extra_body=settings.AI_EXTRA_BODY,
            )
        )

    async def generate_itineraries(
        self,
        prompt: str,
        num_options: int,
        *,
        calls: list[AICallLog] | None = None,
    ) -> AIGenerationResponse:
        """Generate itineraries with retry on failure.

        `calls` collects one AICallLog per
        provider attempt, across retries.
        """
        settings = get_settings()
        last_exc: Exception | None = None

        max_attempts = len(RETRY_DELAYS)
        for attempt in range(max_attempts):
            try:
                return await self.provider.generate_itineraries(
                    prompt,
                    num_options,
                    settings.DEFAULT_AI_MODEL,
                    settings.DEFAULT_REASONING_EFFORT,
                    calls=calls,
                )
            except (AIInputError, LocalRateLimitError):
                # AIInputError: AI diagnosed input as invalid — retrying won't help
                # LocalRateLimitError: our own gate said no — same window, same result
                raise
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "AI provider attempt %d failed (%s): %s",
                    attempt + 1,
                    type(exc).__name__,
                    exc,
                )
                if attempt < max_attempts - 1:
                    delays = (
                        RATE_LIMIT_DELAYS
                        if isinstance(exc, RateLimitError)
                        else RETRY_DELAYS
                    )
                    await asyncio.sleep(delays[attempt])

        raise last_exc  # type: ignore[misc]
