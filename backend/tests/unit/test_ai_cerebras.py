"""Unit tests for CerebrasProvider (app/services/ai/cerebras.py)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.itinerary import (
    AIGenerationResponse,
    DailyActivity,
    DayItinerary,
    ItineraryOption,
)
from app.services.ai.cerebras import CerebrasProvider, _split_prompt
from app.services.ai.json_utils import AIInputError, AIParseError

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


def _make_mock_client(response_json: str) -> MagicMock:
    mock_choice = MagicMock()
    mock_choice.message.content = response_json
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
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
# CerebrasProvider.generate_itineraries tests
# ---------------------------------------------------------------------------


class TestCerebrasProviderGenerate:
    async def test_success_returns_response_and_provider_name(self) -> None:
        provider = CerebrasProvider(api_key="test-key")
        response_json = _make_valid_response_json(num_options=1)
        mock_client = _make_mock_client(response_json)

        with patch.object(provider, "_make_client", return_value=mock_client):
            response, provider_name = await provider.generate_itineraries(
                "[SYSTEM]\nSystem\n[USER]\nUser", 1, "gpt-oss-120b"
            )

        assert provider_name == "cerebras"
        assert isinstance(response, AIGenerationResponse)
        assert len(response.options) == 1
        assert response.options[0].destination_name == "Paris"

    async def test_passes_model_to_client(self) -> None:
        provider = CerebrasProvider(api_key="test-key")
        mock_client = _make_mock_client(_make_valid_response_json())

        with patch.object(provider, "_make_client", return_value=mock_client):
            await provider.generate_itineraries("[SYSTEM]\nS\n[USER]\nU", 1, "my-model")

        create_call = mock_client.chat.completions.create
        assert create_call.call_args.kwargs["model"] == "my-model"

    async def test_passes_reasoning_params_to_client(self) -> None:
        provider = CerebrasProvider(api_key="test-key")
        mock_client = _make_mock_client(_make_valid_response_json())

        with patch.object(provider, "_make_client", return_value=mock_client):
            await provider.generate_itineraries(
                "[SYSTEM]\nS\n[USER]\nU", 1, "gpt-oss-120b", reasoning_effort="low"
            )

        kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert kwargs["reasoning_format"] == "hidden"
        assert kwargs["reasoning_effort"] == "low"

    async def test_sends_system_and_user_messages(self) -> None:
        provider = CerebrasProvider(api_key="test-key")
        mock_client = _make_mock_client(_make_valid_response_json())

        with patch.object(provider, "_make_client", return_value=mock_client):
            await provider.generate_itineraries(
                "[SYSTEM]\nSystem text\n[USER]\nUser text", 1, "model"
            )

        messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
        assert messages[0] == {"role": "system", "content": "System text"}
        assert messages[1] == {"role": "user", "content": "User text"}

    async def test_wrong_option_count_raises_value_error(self) -> None:
        provider = CerebrasProvider(api_key="test-key")
        mock_client = _make_mock_client(_make_valid_response_json(num_options=1))

        with (
            patch.object(provider, "_make_client", return_value=mock_client),
            pytest.raises(ValueError, match="expected 3"),
        ):
            await provider.generate_itineraries("[SYSTEM]\nS\n[USER]\nU", 3, "model")

    async def test_invalid_json_raises_ai_parse_error(self) -> None:
        provider = CerebrasProvider(api_key="test-key")
        mock_client = _make_mock_client("not valid json at all")

        with (
            patch.object(provider, "_make_client", return_value=mock_client),
            pytest.raises(AIParseError),
        ):
            await provider.generate_itineraries("[SYSTEM]\nS\n[USER]\nU", 1, "model")

    async def test_none_content_raises_ai_parse_error(self) -> None:
        provider = CerebrasProvider(api_key="test-key")
        mock_client = _make_mock_client(None)  # type: ignore[arg-type]

        with (
            patch.object(provider, "_make_client", return_value=mock_client),
            pytest.raises(AIParseError),
        ):
            await provider.generate_itineraries("[SYSTEM]\nS\n[USER]\nU", 1, "model")

    async def test_markdown_wrapped_json_succeeds(self) -> None:
        provider = CerebrasProvider(api_key="test-key")
        fenced = f"```json\n{_make_valid_response_json(num_options=1)}\n```"
        mock_client = _make_mock_client(fenced)

        with patch.object(provider, "_make_client", return_value=mock_client):
            response, provider_name = await provider.generate_itineraries(
                "[SYSTEM]\nS\n[USER]\nU", 1, "model"
            )

        assert isinstance(response, AIGenerationResponse)
        assert len(response.options) == 1

    async def test_wrong_schema_raises_ai_parse_error(self) -> None:
        provider = CerebrasProvider(api_key="test-key")
        mock_client = _make_mock_client(json.dumps({"wrong_key": []}))

        with (
            patch.object(provider, "_make_client", return_value=mock_client),
            pytest.raises(AIParseError),
        ):
            await provider.generate_itineraries("[SYSTEM]\nS\n[USER]\nU", 1, "model")

    async def test_error_envelope_raises_ai_input_error(self) -> None:
        provider = CerebrasProvider(api_key="test-key")
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
        provider = CerebrasProvider(api_key="test-key")
        error_response = json.dumps({"error": {}})
        mock_client = _make_mock_client(error_response)

        with (
            patch.object(provider, "_make_client", return_value=mock_client),
            pytest.raises(AIInputError) as exc_info,
        ):
            await provider.generate_itineraries("[SYSTEM]\nS\n[USER]\nU", 1, "model")

        assert exc_info.value.field == "general"
