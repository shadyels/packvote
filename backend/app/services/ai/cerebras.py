import logging

from cerebras.cloud.sdk import AsyncCerebras
from pydantic import ValidationError

from app.schemas.itinerary import AIGenerationResponse
from app.services.ai.base import AIProvider
from app.services.ai.json_utils import AIInputError, AIParseError, extract_json
from app.services.ai.rate_limiter import get_limiter

logger = logging.getLogger(__name__)


def _split_prompt(prompt: str) -> tuple[str, str]:
    parts = prompt.split("\n[USER]\n", maxsplit=1)
    system = parts[0].removeprefix("[SYSTEM]\n").strip()
    user = parts[1].strip() if len(parts) > 1 else ""
    return system, user


class CerebrasProvider(AIProvider):
    """Cerebras inference provider — primary AI provider.

    Uses AsyncCerebras with gpt-oss-120b. reasoning_format="hidden" suppresses
    the reasoning channel so message.content is JSON-only, matching the
    ITINERARY_PROMPT_V3 contract. reasoning_effort is caller-supplied (default
    "low") — escalate via DEFAULT_REASONING_EFFORT env var if prompt adherence
    regresses. disable_reasoning is GLM-only and must not be used here.
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
        reasoning_effort: str = "low",
    ) -> tuple[AIGenerationResponse, str]:
        system_msg, user_msg = _split_prompt(prompt)
        estimated_tokens = (len(system_msg) + len(user_msg)) // 4 + 16384
        limiter = get_limiter()
        reservation = await limiter.reserve(estimated_tokens)
        client = self._make_client()
        try:
            completion = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                response_format={"type": "json_object"},
                reasoning_format="hidden",
                reasoning_effort=reasoning_effort,
                temperature=0.7,
                max_tokens=16384,
            )
        except Exception:
            await limiter.commit(reservation, estimated_tokens)
            raise
        actual_tokens = (
            completion.usage.total_tokens
            if completion.usage is not None
            else estimated_tokens
        )
        await limiter.commit(reservation, actual_tokens)
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
                "Cerebras response JSON extraction failed. Raw: %.2000s",
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
        # AI sometimes omits option_title despite schema instructions.
        # Inject a fallback before validation to avoid a hard failure.
        for opt in data.get("options", []):
            if isinstance(opt, dict) and not opt.get("option_title"):
                logger.warning(
                    "AI omitted option_title for destination=%s — applying fallback",
                    opt.get("destination_name", "<unknown>"),
                )
                opt["option_title"] = opt.get("destination_name", "")
        try:
            response = AIGenerationResponse.model_validate(data)
        except ValidationError as exc:
            logger.warning(
                "Cerebras response failed schema validation: %s. Raw: %.2000s",
                exc,
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
