from app.schemas.itinerary import AIGenerationResponse
from app.services.ai.base import AIProvider


class GroqProvider(AIProvider):
    """Groq free tier — fallback AI provider.

    Used when HuggingFace credits are exhausted or requests fail.
    Implements the same interface as HuggingFaceProvider.
    """

    BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def generate_itineraries(
        self,
        prompt: str,
        num_options: int,
        model: str,
    ) -> AIGenerationResponse:
        # TODO: implement in AI pipeline step
        raise NotImplementedError

    async def generate_followup_survey(
        self,
        prompt: str,
        model: str,
    ) -> list[str]:
        # TODO: implement in AI pipeline step
        raise NotImplementedError

    async def organize_preferences(
        self,
        prompt: str,
        model: str,
    ) -> dict:
        # TODO: implement in AI pipeline step
        raise NotImplementedError
