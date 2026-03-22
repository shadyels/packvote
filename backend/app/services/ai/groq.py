import logging

from huggingface_hub import AsyncInferenceClient
from pydantic import ValidationError

from app.schemas.itinerary import AIGenerationResponse
from app.services.ai.base import AIProvider
from app.services.ai.huggingface import _split_prompt
from app.services.ai.json_utils import AIParseError, extract_json

logger = logging.getLogger(__name__)


class GroqProvider(AIProvider):
    """Groq free tier — fallback AI provider.

    Used when HuggingFace credits are exhausted or requests fail.
    Implements the same interface as HuggingFaceProvider via Groq's OpenAI-compatible API.
    """

    BASE_URL = "https://api.groq.com/openai/v1"
    GROQ_MODEL = "llama-3.3-70b-versatile"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def _make_client(self) -> AsyncInferenceClient:
        return AsyncInferenceClient(base_url=self.BASE_URL, api_key=self.api_key)

    async def generate_itineraries(
        self,
        prompt: str,
        num_options: int,
        model: str,
    ) -> tuple[AIGenerationResponse, str]:
        system_msg, user_msg = _split_prompt(prompt)
        client = self._make_client()
        completion = await client.chat.completions.create(
            model=self.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=8192,
        )
        raw_text = completion.choices[0].message.content
        try:
            data = extract_json(raw_text)
        except AIParseError:
            logger.warning(
                "Groq response JSON extraction failed. Raw (first 500): %.500s",
                raw_text,
            )
            raise
        try:
            response = AIGenerationResponse.model_validate(data)
        except ValidationError as exc:
            logger.warning(
                "Groq response failed schema validation. Raw (first 500): %.500s",
                raw_text,
            )
            raise AIParseError(str(exc), raw_text=raw_text) from exc
        if len(response.options) != num_options:
            raise ValueError(
                f"AI returned {len(response.options)} options, expected {num_options}"
            )
        return response, "groq"

    async def generate_followup_survey(
        self,
        prompt: str,
        model: str,
    ) -> list[str]:
        # TODO: implement in iteration step
        raise NotImplementedError

    async def organize_preferences(
        self,
        prompt: str,
        model: str,
    ) -> dict:
        # TODO: implement in iteration step
        raise NotImplementedError
