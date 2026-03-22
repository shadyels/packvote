import logging

from huggingface_hub import AsyncInferenceClient
from pydantic import ValidationError

from app.schemas.itinerary import AIGenerationResponse
from app.services.ai.base import AIProvider
from app.services.ai.json_utils import AIParseError, extract_json

logger = logging.getLogger(__name__)


def _split_prompt(prompt: str) -> tuple[str, str]:
    """Split a [SYSTEM]/[USER] delimited prompt string into two messages."""
    parts = prompt.split("\n[USER]\n", maxsplit=1)
    system = parts[0].removeprefix("[SYSTEM]\n").strip()
    user = parts[1].strip() if len(parts) > 1 else ""
    return system, user


class HuggingFaceProvider(AIProvider):
    """HuggingFace Inference Providers — default AI provider.

    Routes requests via the HuggingFace OpenAI-compatible inference endpoint.
    Uses Qwen2.5-72B-Instruct by default.
    """

    BASE_URL = "https://api-inference.huggingface.co/v1"

    def __init__(self, api_token: str) -> None:
        self.api_token = api_token

    def _make_client(self) -> AsyncInferenceClient:
        return AsyncInferenceClient(base_url=self.BASE_URL, api_key=self.api_token)

    async def generate_itineraries(
        self,
        prompt: str,
        num_options: int,
        model: str,
    ) -> tuple[AIGenerationResponse, str]:
        system_msg, user_msg = _split_prompt(prompt)
        client = self._make_client()
        completion = await client.chat.completions.create(
            model=model,
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
                "HuggingFace response JSON extraction failed. Raw (first 500): %.500s",
                raw_text,
            )
            raise
        try:
            response = AIGenerationResponse.model_validate(data)
        except ValidationError as exc:
            logger.warning(
                "HuggingFace response failed schema validation. Raw (first 500): %.500s",
                raw_text,
            )
            raise AIParseError(str(exc), raw_text=raw_text) from exc
        if len(response.options) != num_options:
            raise ValueError(
                f"AI returned {len(response.options)} options, expected {num_options}"
            )
        return response, "huggingface"

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
