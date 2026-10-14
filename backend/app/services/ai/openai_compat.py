import logging
import time
from datetime import UTC, datetime
from typing import Any

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.models.ai_call_log import AICallLog
from app.schemas.itinerary import AIGenerationResponse
from app.services.ai.base import AIProvider
from app.services.ai.json_utils import AIInputError, AIParseError, extract_json
from app.services.ai.rate_limiter import get_limiter

logger = logging.getLogger(__name__)

MAX_OUTPUT_TOKENS = 16_384


def _split_prompt(prompt: str) -> tuple[str, str]:
    parts = prompt.split("\n[USER]\n", maxsplit=1)
    system = parts[0].removeprefix("[SYSTEM]\n").strip()
    user = parts[1].strip() if len(parts) > 1 else ""
    return system, user


class OpenAICompatProvider(AIProvider):
    """Inference provider for any OpenAI-compatible chat-completions endpoint.

    Gemini, OpenRouter, Mistral, Groq and Cerebras all expose this API shape, so
    switching provider is a config change (AI_BASE_URL / AI_API_KEY /
    DEFAULT_AI_MODEL) rather than a code change. Defaults target Gemini's free
    tier; see docs/AI-ARCHITECTURE.md.

    `extra_body` carries the vendor-specific knobs the OpenAI schema has no field
    for. For Gemini it disables the thinking pass, which is essential: thinking
    tokens are drawn from the same max_tokens budget as the response, so leaving
    it on silently truncates the JSON (finish_reason="length").

    `reasoning_effort` is only sent when it is not "none" — Gemini rejects
    reasoning_effort and thinking_config supplied together.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        provider_name: str,
        extra_body: dict[str, Any] | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.provider_name = provider_name
        self.extra_body = extra_body or {}

    def _make_client(self) -> AsyncOpenAI:
        # AIService owns retries; SDK retries would hide attempts from ai_call_logs.
        return AsyncOpenAI(
            api_key=self.api_key, base_url=self.base_url, timeout=180, max_retries=0
        )

    async def generate_itineraries(
        self,
        prompt: str,
        num_options: int,
        model: str,
        reasoning_effort: str = "none",
        *,
        calls: list[AICallLog] | None = None,
    ) -> tuple[AIGenerationResponse, str]:
        system_msg, user_msg = _split_prompt(prompt)
        estimated_tokens = (len(system_msg) + len(user_msg)) // 4 + MAX_OUTPUT_TOKENS
        limiter = get_limiter()
        reservation = await limiter.reserve(estimated_tokens)
        # One row per network attempt; generation.py stamps trip context and
        # persists. ponytail: provider layer builds ORM rows directly — swap for
        # a plain dataclass if services/ai/ must stay DB-agnostic.
        log = AICallLog(
            provider=self.provider_name,
            model_used=model,
            prompt=prompt,
            response_valid=False,
            created_at=datetime.now(UTC),
        )
        if calls is not None:
            calls.append(log)
        client = self._make_client()
        extra_kwargs: dict[str, Any] = {}
        if reasoning_effort != "none":
            extra_kwargs["reasoning_effort"] = reasoning_effort
        if self.extra_body:
            extra_kwargs["extra_body"] = self.extra_body
        t_start = time.monotonic()
        try:
            completion = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=MAX_OUTPUT_TOKENS,
                **extra_kwargs,
            )
        except Exception as exc:
            log.latency_ms = int((time.monotonic() - t_start) * 1000)
            log.error_message = str(exc)
            await limiter.commit(reservation, estimated_tokens)
            raise
        log.latency_ms = int((time.monotonic() - t_start) * 1000)
        usage = completion.usage
        await limiter.commit(
            reservation, usage.total_tokens if usage is not None else estimated_tokens
        )
        log.model_used = completion.model or model
        if usage is not None:
            log.token_count_input = usage.prompt_tokens
            log.token_count_output = usage.completion_tokens
            log.token_count_total = usage.total_tokens
        try:
            choice = completion.choices[0]
            log.finish_reason = choice.finish_reason
            log.raw_response = choice.message.content
            if choice.finish_reason == "length":
                logger.warning(
                    "%s response truncated (finish_reason=length) — JSON will be "
                    "incomplete. Check that the provider's thinking/reasoning pass "
                    "is disabled; it draws from the same max_tokens budget.",
                    self.provider_name,
                )
            response = self._parse_response(choice.message.content, num_options)
        except Exception as exc:
            log.error_message = str(exc)
            raise
        log.response_valid = True
        return response, self.provider_name

    def _parse_response(
        self, raw_text: str | None, num_options: int
    ) -> AIGenerationResponse:
        try:
            data = extract_json(raw_text)
        except AIParseError:
            logger.warning(
                "%s response JSON extraction failed. Raw: %.2000s",
                self.provider_name,
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
                "%s response failed schema validation: %s. Raw: %.2000s",
                self.provider_name,
                exc,
                raw_text,
            )
            raise AIParseError(str(exc), raw_text=raw_text) from exc
        if len(response.options) != num_options:
            raise ValueError(
                f"AI returned {len(response.options)} options, expected {num_options}"
            )
        return response

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
