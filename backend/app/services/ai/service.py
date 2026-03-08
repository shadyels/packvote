from app.core.config import get_settings
from app.schemas.itinerary import AIGenerationResponse
from app.services.ai.base import AIProvider
from app.services.ai.groq import GroqProvider
from app.services.ai.huggingface import HuggingFaceProvider


class AIService:
    """Orchestrates AI provider selection, fallback, and retry logic.

    Provider selection order:
    1. Primary provider (HuggingFace by default, configurable)
    2. Fallback provider (Groq) if primary fails or is exhausted

    Failed requests use exponential backoff — never immediate retry.
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
    ) -> AIGenerationResponse:
        settings = get_settings()
        resolved_model = model or settings.DEFAULT_AI_MODEL
        # TODO: implement with retry + fallback in AI pipeline step
        return await self.primary.generate_itineraries(prompt, num_options, resolved_model)

    async def generate_followup_survey(
        self,
        prompt: str,
        model: str | None = None,
    ) -> list[str]:
        settings = get_settings()
        resolved_model = model or settings.DEFAULT_AI_MODEL
        # TODO: implement with retry + fallback in AI pipeline step
        return await self.primary.generate_followup_survey(prompt, resolved_model)
