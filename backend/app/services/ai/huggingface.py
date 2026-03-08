from app.schemas.itinerary import AIGenerationResponse
from app.services.ai.base import AIProvider


class HuggingFaceProvider(AIProvider):
    """HuggingFace Inference Providers — default AI provider.

    Routes requests via the HuggingFace Inference API which supports
    multiple backend providers (Sambanova, Together AI, Cerebras, Groq).
    Uses Qwen2.5-72B-Instruct by default.
    """

    BASE_URL = "https://api-inference.huggingface.co/models"

    def __init__(self, api_token: str) -> None:
        self.api_token = api_token

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
