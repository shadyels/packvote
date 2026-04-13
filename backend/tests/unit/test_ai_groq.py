"""Unit tests for GroqProvider (app/services/ai/groq.py)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.itinerary import AIGenerationResponse, ItineraryOption
from app.services.ai.groq import GroqProvider
from app.services.ai.json_utils import AIInputError, AIParseError

# ---------------------------------------------------------------------------
# Helpers (reuse the same builder used in test_ai_huggingface)
# ---------------------------------------------------------------------------


def _make_valid_response_json(num_options: int = 1) -> str:
    option = ItineraryOption(
        option_title="Neon & Noodles Run",
        destination_name="Tokyo",
        destination_description="City of contrasts",
        daily_itinerary=[],
        total_estimated_budget=2000.0,
        currency="USD",
        match_reasoning="Excellent match",
        highlights=["Shibuya", "Asakusa"],
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
# Tests
# ---------------------------------------------------------------------------


class TestGroqProvider:
    async def test_success_returns_groq_provider_name(self) -> None:
        provider = GroqProvider(api_key="test-key")
        mock_client = _make_mock_client(_make_valid_response_json())

        with patch.object(provider, "_make_client", return_value=mock_client):
            response, provider_name = await provider.generate_itineraries(
                "[SYSTEM]\nSystem\n[USER]\nUser", 1, "huggingface-model-id"
            )

        assert provider_name == "groq"
        assert isinstance(response, AIGenerationResponse)

    async def test_hardcodes_groq_model_ignores_input(self) -> None:
        """Groq always uses its own model regardless of what model arg is passed."""
        provider = GroqProvider(api_key="test-key")
        mock_client = _make_mock_client(_make_valid_response_json())

        with patch.object(provider, "_make_client", return_value=mock_client):
            await provider.generate_itineraries(
                "[SYSTEM]\nS\n[USER]\nU", 1, "Qwen/Qwen2.5-72B-Instruct"
            )

        create_call = mock_client.chat.completions.create
        assert create_call.call_args.kwargs["model"] == "llama-3.3-70b-versatile"

    async def test_groq_model_constant_value(self) -> None:
        assert GroqProvider.GROQ_MODEL == "llama-3.3-70b-versatile"

    async def test_wrong_option_count_raises_value_error(self) -> None:
        provider = GroqProvider(api_key="test-key")
        mock_client = _make_mock_client(_make_valid_response_json(num_options=1))

        with (
            patch.object(provider, "_make_client", return_value=mock_client),
            pytest.raises(ValueError, match="expected 2"),
        ):
            await provider.generate_itineraries("[SYSTEM]\nS\n[USER]\nU", 2, "model")

    async def test_reuses_split_prompt_from_huggingface(self) -> None:
        """GroqProvider imports _split_prompt from huggingface module."""
        provider = GroqProvider(api_key="test-key")
        mock_client = _make_mock_client(_make_valid_response_json())

        with patch.object(provider, "_make_client", return_value=mock_client):
            await provider.generate_itineraries(
                "[SYSTEM]\nSystem part\n[USER]\nUser part", 1, "model"
            )

        messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
        assert messages[0]["content"] == "System part"
        assert messages[1]["content"] == "User part"

    async def test_uses_groq_base_url(self) -> None:
        assert GroqProvider.BASE_URL == "https://api.groq.com/openai/v1"

    async def test_invalid_json_raises_ai_parse_error(self) -> None:
        provider = GroqProvider(api_key="test-key")
        mock_client = _make_mock_client("not valid json at all")

        with (
            patch.object(provider, "_make_client", return_value=mock_client),
            pytest.raises(AIParseError),
        ):
            await provider.generate_itineraries("[SYSTEM]\nS\n[USER]\nU", 1, "model")

    async def test_none_content_raises_ai_parse_error(self) -> None:
        provider = GroqProvider(api_key="test-key")
        mock_client = _make_mock_client(None)  # type: ignore[arg-type]

        with (
            patch.object(provider, "_make_client", return_value=mock_client),
            pytest.raises(AIParseError),
        ):
            await provider.generate_itineraries("[SYSTEM]\nS\n[USER]\nU", 1, "model")

    async def test_markdown_wrapped_json_succeeds(self) -> None:
        provider = GroqProvider(api_key="test-key")
        fenced = f"```json\n{_make_valid_response_json(num_options=1)}\n```"
        mock_client = _make_mock_client(fenced)

        with patch.object(provider, "_make_client", return_value=mock_client):
            response, provider_name = await provider.generate_itineraries(
                "[SYSTEM]\nS\n[USER]\nU", 1, "model"
            )

        assert isinstance(response, AIGenerationResponse)
        assert len(response.options) == 1

    async def test_wrong_schema_raises_ai_parse_error(self) -> None:
        provider = GroqProvider(api_key="test-key")
        mock_client = _make_mock_client(json.dumps({"wrong_key": []}))

        with (
            patch.object(provider, "_make_client", return_value=mock_client),
            pytest.raises(AIParseError),
        ):
            await provider.generate_itineraries("[SYSTEM]\nS\n[USER]\nU", 1, "model")

    async def test_error_envelope_raises_ai_input_error(self) -> None:
        provider = GroqProvider(api_key="test-key")
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
        assert err.field == "destination"
        assert "Cancun" in err.suggestion
