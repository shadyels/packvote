import asyncio
import logging

from app.core.config import get_settings
from app.schemas.itinerary import AIGenerationResponse
from app.services.ai.base import AIProvider
from app.services.ai.cerebras import CerebrasProvider
from app.services.ai.json_utils import AIInputError

logger = logging.getLogger(__name__)

RETRY_DELAYS = [1.0, 2.0, 4.0]  # seconds between attempts


class AIService:
    """Orchestrates AI provider selection and retry logic.

    Retries the Cerebras provider up to 3 times with exponential backoff.
    On total exhaustion re-raises the last exception.
    """

    def __init__(self, provider: AIProvider) -> None:
        self.provider = provider

    @classmethod
    def from_settings(cls) -> "AIService":
        settings = get_settings()
        return cls(provider=CerebrasProvider(api_key=settings.CEREBRAS_API_KEY))

    async def generate_itineraries(
        self,
        prompt: str,
        num_options: int,
        model: str | None = None,
    ) -> tuple[AIGenerationResponse, str]:
        """Generate itineraries with retry on failure.

        Returns (response, provider_name).
        """
        settings = get_settings()
        resolved_model = model or settings.DEFAULT_AI_MODEL
        last_exc: Exception | None = None

        for attempt, delay in enumerate(RETRY_DELAYS):
            try:
                return await self.provider.generate_itineraries(
                    prompt, num_options, resolved_model
                )
            except AIInputError:
                # AI diagnosed the input as invalid — retrying won't help
                raise
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "Cerebras attempt %d failed (%s): %s",
                    attempt + 1,
                    type(exc).__name__,
                    exc,
                )
                if attempt < len(RETRY_DELAYS) - 1:
                    await asyncio.sleep(delay)

        raise last_exc  # type: ignore[misc]

    async def generate_followup_survey(
        self,
        prompt: str,
        model: str | None = None,
    ) -> list[str]:
        settings = get_settings()
        resolved_model = model or settings.DEFAULT_AI_MODEL
        return await self.provider.generate_followup_survey(prompt, resolved_model)
