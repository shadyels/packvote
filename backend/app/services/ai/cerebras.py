import logging

from cerebras.cloud.sdk import AsyncCerebras
from pydantic import ValidationError

from app.schemas.itinerary import AIGenerationResponse
from app.services.ai.base import AIProvider
from app.services.ai.json_utils import AIInputError, AIParseError, extract_json

logger = logging.getLogger(__name__)


def _split_prompt(prompt: str) -> tuple[str, str]:
    parts = prompt.split("\n[USER]\n", maxsplit=1)
    system = parts[0].removeprefix("[SYSTEM]\n").strip()
    user = parts[1].strip() if len(parts) > 1 else ""
    return system, user


class CerebrasProvider(AIProvider):
    """Cerebras inference provider — primary AI provider.

    Uses AsyncCerebras client with Qwen-3-235B-A22B-Instruct.
    Qwen-3 Instruct is a non-thinking checkpoint — disable_reasoning is
    GLM-family-specific and is intentionally omitted.
    """

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def _make_client(self) -> AsyncCerebras:
        return AsyncCerebras(api_key=self.api_key, timeout=180)

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
            max_tokens=16384,
        )
        choice = completion.choices[0]
        if choice.finish_reason == "length":
            logger.warning(
                "Cerebras response truncated (finish_reason=length) — "
                "JSON will be incomplete; consider reducing trip complexity."
            )
        raw_text = choice.message.content
        try:
            data = extract_json(raw_text)
        except AIParseError:
            logger.warning(
                "Cerebras response JSON extraction failed. Raw (first 500): %.500s",
                raw_text,
            )
            raise
        if "error" in data and isinstance(data["error"], dict):
            err = data["error"]
            raise AIInputError(
                message=err.get("message", "The AI could not process this request."),
                suggestion=err.get("suggestion", ""),
                field=err.get("field", "general"),
            )
        try:
            response = AIGenerationResponse.model_validate(data)
        except ValidationError as exc:
            logger.warning(
                "Cerebras response failed schema validation. Raw (first 500): %.500s",
                raw_text,
            )
            raise AIParseError(str(exc), raw_text=raw_text) from exc
        if len(response.options) != num_options:
            raise ValueError(
                f"AI returned {len(response.options)} options, expected {num_options}"
            )
        return response, "cerebras"

    async def generate_followup_survey(
        self,
        prompt: str,
        model: str,
    ) -> list[str]:
        raise NotImplementedError

    async def organize_preferences(
        self,
        prompt: str,
        model: str,
    ) -> dict:
        raise NotImplementedError
