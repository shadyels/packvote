"""Unit tests for OpenAICompatProvider (app/services/ai/openai_compat.py)."""

from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from openai import AsyncOpenAI

from app.core.config import get_settings
from app.schemas.itinerary import (
    AIGenerationResponse,
    DailyActivity,
    DayItinerary,
    ItineraryOption,
)
from app.services.ai.json_utils import AIInputError, AIParseError
from app.services.ai.openai_compat import OpenAICompatProvider, _split_prompt
from app.services.ai.rate_limiter import GlobalRateLimiter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_valid_response_json(num_options: int = 1) -> str:
    option = ItineraryOption(
        option_title="Bistros & Boulevards",
        destination_name="Paris",
        destination_description="City of Light",
        daily_itinerary=[
            DayItinerary(
                day_number=1,
                title="Arrival",
                activities=[
                    DailyActivity(
                        title="Check in",
                        description="Hotel check-in",
                    )
                ],
            )
        ],
        total_estimated_budget=1500.0,
        currency="EUR",
        match_reasoning="Great match",
        highlights=["Eiffel Tower", "Louvre"],
    )
    return json.dumps({"options": [option.model_dump()] * num_options})


def _fake_completion_payload(content: str) -> dict:
    """Raw OpenAI chat-completion response body, as it comes over the wire."""
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "test-model",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 10,
            "total_tokens": 20,
        },
    }


def _make_provider(extra_body: dict | None = None) -> OpenAICompatProvider:
    return OpenAICompatProvider(
        api_key="test-key",
        base_url="https://example.invalid/v1/",
        provider_name="test-provider",
        extra_body=extra_body,
    )


def _make_mock_client(response_json: str) -> MagicMock:
    mock_choice = MagicMock()
    mock_choice.message.content = response_json
    mock_choice.finish_reason = "stop"
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_completion.usage.total_tokens = 500
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
    return mock_client


# ---------------------------------------------------------------------------
# _split_prompt tests
# ---------------------------------------------------------------------------


class TestSplitPrompt:
    def test_normal_split(self) -> None:
        prompt = "[SYSTEM]\nYou are an assistant.\n[USER]\nPlan a trip."
        system, user = _split_prompt(prompt)
        assert system == "You are an assistant."
        assert user == "Plan a trip."

    def test_no_user_section(self) -> None:
        prompt = "[SYSTEM]\nSystem only prompt."
        system, user = _split_prompt(prompt)
        assert system == "System only prompt."
        assert user == ""

    def test_multiline_sections(self) -> None:
        prompt = "[SYSTEM]\nLine 1\nLine 2\n[USER]\nUser line 1\nUser line 2"
        system, user = _split_prompt(prompt)
        assert system == "Line 1\nLine 2"
        assert user == "User line 1\nUser line 2"

    def test_strips_leading_trailing_whitespace(self) -> None:
        prompt = "[SYSTEM]\n  spaced  \n[USER]\n  user  "
        system, user = _split_prompt(prompt)
        assert system == "spaced"
        assert user == "user"


# ---------------------------------------------------------------------------
# OpenAICompatProvider.generate_itineraries tests
# ---------------------------------------------------------------------------


class TestOpenAICompatProviderGenerate:
    """Tests for OpenAICompatProvider.generate_itineraries.

    Each test patches get_limiter() with a fresh GlobalRateLimiter to
    prevent the global singleton from leaking state between tests.
    """

    @pytest.fixture(autouse=True)
    def fresh_limiter(self) -> None:  # type: ignore[return]
        """Inject a fresh rate limiter so tests are isolated from the singleton."""
        with patch(
            "app.services.ai.openai_compat.get_limiter",
            return_value=GlobalRateLimiter(),
        ):
            yield

    async def test_success_returns_response_and_provider_name(self) -> None:
        provider = _make_provider()
        response_json = _make_valid_response_json(num_options=1)
        mock_client = _make_mock_client(response_json)

        with patch.object(provider, "_make_client", return_value=mock_client):
            response, provider_name = await provider.generate_itineraries(
                "[SYSTEM]\nSystem\n[USER]\nUser", 1, "gemini-2.5-flash"
            )

        assert provider_name == "test-provider"
        assert isinstance(response, AIGenerationResponse)
        assert len(response.options) == 1
        assert response.options[0].destination_name == "Paris"

    async def test_passes_model_to_client(self) -> None:
        provider = _make_provider()
        mock_client = _make_mock_client(_make_valid_response_json())

        with patch.object(provider, "_make_client", return_value=mock_client):
            await provider.generate_itineraries("[SYSTEM]\nS\n[USER]\nU", 1, "my-model")

        create_call = mock_client.chat.completions.create
        assert create_call.call_args.kwargs["model"] == "my-model"

    async def test_reasoning_effort_none_is_omitted(self) -> None:
        """Gemini rejects reasoning_effort and thinking_config together, so
        "none" must drop the param entirely and let extra_body govern."""
        provider = _make_provider()
        mock_client = _make_mock_client(_make_valid_response_json())

        with patch.object(provider, "_make_client", return_value=mock_client):
            await provider.generate_itineraries(
                "[SYSTEM]\nS\n[USER]\nU", 1, "model", reasoning_effort="none"
            )

        kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert "reasoning_effort" not in kwargs

    async def test_non_none_reasoning_effort_is_forwarded(self) -> None:
        provider = _make_provider()
        mock_client = _make_mock_client(_make_valid_response_json())

        with patch.object(provider, "_make_client", return_value=mock_client):
            await provider.generate_itineraries(
                "[SYSTEM]\nS\n[USER]\nU", 1, "model", reasoning_effort="low"
            )

        assert (
            mock_client.chat.completions.create.call_args.kwargs["reasoning_effort"]
            == "low"
        )

    async def test_extra_body_is_forwarded(self) -> None:
        thinking_off = {
            "extra_body": {"google": {"thinking_config": {"thinking_budget": 0}}}
        }
        provider = _make_provider(extra_body=thinking_off)
        mock_client = _make_mock_client(_make_valid_response_json())

        with patch.object(provider, "_make_client", return_value=mock_client):
            await provider.generate_itineraries("[SYSTEM]\nS\n[USER]\nU", 1, "model")

        kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert kwargs["extra_body"] == thinking_off

    async def test_extra_body_serializes_to_top_level_extra_body_field(self) -> None:
        """Regression: the OpenAI SDK flattens extra_body into the top level of the
        request body. Gemini expects a literal `extra_body` field there, so a
        single-level {"google": ...} yields 400 Unknown name "google"."""
        captured: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content))
            return httpx.Response(
                200, json=_fake_completion_payload(_make_valid_response_json())
            )

        provider = _make_provider(extra_body=get_settings().AI_EXTRA_BODY)
        client = AsyncOpenAI(
            api_key="k",
            base_url="https://example.invalid/v1/",
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        )
        with patch.object(provider, "_make_client", return_value=client):
            await provider.generate_itineraries("[SYSTEM]\nS\n[USER]\nU", 1, "model")

        assert "google" not in captured
        assert captured["extra_body"] == {
            "google": {"thinking_config": {"thinking_budget": 0}}
        }

    async def test_empty_extra_body_is_omitted(self) -> None:
        """Providers that reject unknown request fields must not receive an
        empty extra_body."""
        provider = _make_provider(extra_body={})
        mock_client = _make_mock_client(_make_valid_response_json())

        with patch.object(provider, "_make_client", return_value=mock_client):
            await provider.generate_itineraries("[SYSTEM]\nS\n[USER]\nU", 1, "model")

        assert "extra_body" not in mock_client.chat.completions.create.call_args.kwargs

    async def test_requests_json_object_response_format(self) -> None:
        """Must stay json_object, not json_schema — a strict schema would make
        the {"error": {...}} envelope unrepresentable."""
        provider = _make_provider()
        mock_client = _make_mock_client(_make_valid_response_json())

        with patch.object(provider, "_make_client", return_value=mock_client):
            await provider.generate_itineraries("[SYSTEM]\nS\n[USER]\nU", 1, "model")

        kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert kwargs["response_format"] == {"type": "json_object"}

    async def test_sends_system_and_user_messages(self) -> None:
        provider = _make_provider()
        mock_client = _make_mock_client(_make_valid_response_json())

        with patch.object(provider, "_make_client", return_value=mock_client):
            await provider.generate_itineraries(
                "[SYSTEM]\nSystem text\n[USER]\nUser text", 1, "model"
            )

        messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
        assert messages[0] == {"role": "system", "content": "System text"}
        assert messages[1] == {"role": "user", "content": "User text"}

    async def test_wrong_option_count_raises_value_error(self) -> None:
        provider = _make_provider()
        mock_client = _make_mock_client(_make_valid_response_json(num_options=1))

        with (
            patch.object(provider, "_make_client", return_value=mock_client),
            pytest.raises(ValueError, match="expected 3"),
        ):
            await provider.generate_itineraries("[SYSTEM]\nS\n[USER]\nU", 3, "model")

    async def test_invalid_json_raises_ai_parse_error(self) -> None:
        provider = _make_provider()
        mock_client = _make_mock_client("not valid json at all")

        with (
            patch.object(provider, "_make_client", return_value=mock_client),
            pytest.raises(AIParseError),
        ):
            await provider.generate_itineraries("[SYSTEM]\nS\n[USER]\nU", 1, "model")

    async def test_none_content_raises_ai_parse_error(self) -> None:
        provider = _make_provider()
        mock_client = _make_mock_client(None)  # type: ignore[arg-type]

        with (
            patch.object(provider, "_make_client", return_value=mock_client),
            pytest.raises(AIParseError),
        ):
            await provider.generate_itineraries("[SYSTEM]\nS\n[USER]\nU", 1, "model")

    async def test_markdown_wrapped_json_succeeds(self) -> None:
        provider = _make_provider()
        fenced = f"```json\n{_make_valid_response_json(num_options=1)}\n```"
        mock_client = _make_mock_client(fenced)

        with patch.object(provider, "_make_client", return_value=mock_client):
            response, provider_name = await provider.generate_itineraries(
                "[SYSTEM]\nS\n[USER]\nU", 1, "model"
            )

        assert isinstance(response, AIGenerationResponse)
        assert len(response.options) == 1

    async def test_wrong_schema_raises_ai_parse_error(self) -> None:
        provider = _make_provider()
        mock_client = _make_mock_client(json.dumps({"wrong_key": []}))

        with (
            patch.object(provider, "_make_client", return_value=mock_client),
            pytest.raises(AIParseError),
        ):
            await provider.generate_itineraries("[SYSTEM]\nS\n[USER]\nU", 1, "model")

    async def test_error_envelope_raises_ai_input_error(self) -> None:
        provider = _make_provider()
        error_response = json.dumps(
            {
                "error": {
                    "message": "I couldn't find a destination matching 'xxxxnotaplace'.",
                    "suggestion": "Try 'Cancun, Mexico' or 'Bali, Indonesia'.",
                    "field": "destination",
                }
            }
        )
        mock_client = _make_mock_client(error_response)

        with (
            patch.object(provider, "_make_client", return_value=mock_client),
            pytest.raises(AIInputError) as exc_info,
        ):
            await provider.generate_itineraries("[SYSTEM]\nS\n[USER]\nU", 1, "model")

        err = exc_info.value
        assert "xxxxnotaplace" in err.ai_message
        assert err.field == "destination"
        assert "Cancun" in err.suggestion

    async def test_error_envelope_missing_fields_uses_defaults(self) -> None:
        provider = _make_provider()
        error_response = json.dumps({"error": {}})
        mock_client = _make_mock_client(error_response)

        with (
            patch.object(provider, "_make_client", return_value=mock_client),
            pytest.raises(AIInputError) as exc_info,
        ):
            await provider.generate_itineraries("[SYSTEM]\nS\n[USER]\nU", 1, "model")

        assert exc_info.value.field == "general"
