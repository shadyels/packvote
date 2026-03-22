"""Unit tests for AIService retry/fallback logic (app/services/ai/service.py).

All tests use AsyncMock providers — no real API calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.itinerary import AIGenerationResponse, ItineraryOption
from app.services.ai.service import AIService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_option(destination: str = "Paris") -> ItineraryOption:
    return ItineraryOption(
        destination_name=destination,
        destination_description="A great city",
        daily_itinerary=[],
        total_estimated_budget=1500.0,
        currency="EUR",
        match_reasoning="Perfect match",
        highlights=["Landmark 1"],
    )


def _make_response(destination: str = "Paris") -> AIGenerationResponse:
    return AIGenerationResponse(options=[_make_option(destination)])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAIServiceRetry:
    async def test_primary_succeeds_first_attempt(self) -> None:
        mock_result = (_make_response(), "huggingface")
        primary = AsyncMock()
        primary.generate_itineraries.return_value = mock_result
        service = AIService(primary=primary)

        with patch("asyncio.sleep") as mock_sleep:
            result = await service.generate_itineraries("prompt", 1, "model")

        assert result == mock_result
        primary.generate_itineraries.assert_called_once()
        mock_sleep.assert_not_called()

    async def test_primary_fails_once_then_succeeds(self) -> None:
        mock_result = (_make_response(), "huggingface")
        primary = AsyncMock()
        primary.generate_itineraries.side_effect = [
            RuntimeError("transient error"),
            mock_result,
        ]
        service = AIService(primary=primary)

        with patch("asyncio.sleep") as mock_sleep:
            result = await service.generate_itineraries("prompt", 1, "model")

        assert result == mock_result
        assert primary.generate_itineraries.call_count == 2
        mock_sleep.assert_called_once_with(1.0)

    async def test_primary_fails_all_fallback_succeeds(self) -> None:
        mock_result = (_make_response("Tokyo"), "groq")
        primary = AsyncMock()
        primary.generate_itineraries.side_effect = RuntimeError("always fail")
        fallback = AsyncMock()
        fallback.generate_itineraries.return_value = mock_result
        service = AIService(primary=primary, fallback=fallback)

        with patch("asyncio.sleep") as mock_sleep:
            result = await service.generate_itineraries("prompt", 1, "model")

        assert result == mock_result
        assert primary.generate_itineraries.call_count == 3
        fallback.generate_itineraries.assert_called_once()
        # sleep called after attempt 0 (1.0s) and attempt 1 (2.0s), not after attempt 2
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1.0)
        mock_sleep.assert_any_call(2.0)

    async def test_primary_fails_all_no_fallback_raises(self) -> None:
        primary = AsyncMock()
        primary.generate_itineraries.side_effect = RuntimeError("primary fail")
        service = AIService(primary=primary, fallback=None)

        with patch("asyncio.sleep"), pytest.raises(RuntimeError, match="primary fail"):
            await service.generate_itineraries("prompt", 1, "model")

    async def test_primary_and_fallback_both_fail_raises_last(self) -> None:
        primary = AsyncMock()
        primary.generate_itineraries.side_effect = RuntimeError("primary fail")
        fallback = AsyncMock()
        fallback.generate_itineraries.side_effect = RuntimeError("fallback fail")
        service = AIService(primary=primary, fallback=fallback)

        with patch("asyncio.sleep"), pytest.raises(RuntimeError, match="fallback fail"):
            await service.generate_itineraries("prompt", 1, "model")

    async def test_explicit_model_passed_to_provider(self) -> None:
        mock_result = (_make_response(), "huggingface")
        primary = AsyncMock()
        primary.generate_itineraries.return_value = mock_result
        service = AIService(primary=primary)

        with patch("asyncio.sleep"):
            await service.generate_itineraries("prompt", 1, "my-custom-model")

        call_args = primary.generate_itineraries.call_args
        assert call_args[0][2] == "my-custom-model"

    async def test_default_model_resolved_from_settings(self) -> None:
        mock_result = (_make_response(), "huggingface")
        primary = AsyncMock()
        primary.generate_itineraries.return_value = mock_result
        service = AIService(primary=primary)

        with patch("asyncio.sleep"), patch("app.services.ai.service.get_settings") as mock_settings:
            mock_settings.return_value.DEFAULT_AI_MODEL = "Qwen2.5-72B-Instruct"
            await service.generate_itineraries("prompt", 1, model=None)

        call_args = primary.generate_itineraries.call_args
        assert call_args[0][2] == "Qwen2.5-72B-Instruct"
