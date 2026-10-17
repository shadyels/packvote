"""Unit tests for AIService retry logic (app/services/ai/service.py).

All tests use AsyncMock providers — no real API calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.itinerary import AIGenerationResponse, ItineraryOption
from app.services.ai.json_utils import AIInputError
from app.services.ai.service import AIService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_option(destination: str = "Paris") -> ItineraryOption:
    return ItineraryOption(
        option_title="City Culture Trip",
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
        mock_result = _make_response()
        provider = AsyncMock()
        provider.generate_itineraries.return_value = mock_result
        service = AIService(provider=provider)

        with patch("asyncio.sleep") as mock_sleep:
            result = await service.generate_itineraries("prompt", 1)

        assert result == mock_result
        provider.generate_itineraries.assert_called_once()
        mock_sleep.assert_not_called()

    async def test_primary_fails_once_then_succeeds(self) -> None:
        mock_result = _make_response()
        provider = AsyncMock()
        provider.generate_itineraries.side_effect = [
            RuntimeError("transient error"),
            mock_result,
        ]
        service = AIService(provider=provider)

        with patch("asyncio.sleep") as mock_sleep:
            result = await service.generate_itineraries("prompt", 1)

        assert result == mock_result
        assert provider.generate_itineraries.call_count == 2
        mock_sleep.assert_awaited_once()  # a retry backoff happened; delay value not pinned

    async def test_primary_fails_all_raises(self) -> None:
        provider = AsyncMock()
        provider.generate_itineraries.side_effect = RuntimeError("always fail")
        service = AIService(provider=provider)

        with patch("asyncio.sleep"), pytest.raises(RuntimeError, match="always fail"):
            await service.generate_itineraries("prompt", 1)

        assert provider.generate_itineraries.call_count == 3

    async def test_default_model_resolved_from_settings(self) -> None:
        mock_result = _make_response()
        provider = AsyncMock()
        provider.generate_itineraries.return_value = mock_result
        service = AIService(provider=provider)

        with (
            patch("asyncio.sleep"),
            patch("app.services.ai.service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.DEFAULT_AI_MODEL = "gemini-2.5-flash"
            mock_settings.return_value.DEFAULT_REASONING_EFFORT = "low"
            await service.generate_itineraries("prompt", 1)

        call_args = provider.generate_itineraries.call_args
        assert call_args[0][2] == "gemini-2.5-flash"

    async def test_default_reasoning_effort_resolved_from_settings(self) -> None:
        mock_result = _make_response()
        provider = AsyncMock()
        provider.generate_itineraries.return_value = mock_result
        service = AIService(provider=provider)

        with (
            patch("asyncio.sleep"),
            patch("app.services.ai.service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.DEFAULT_AI_MODEL = "gemini-2.5-flash"
            mock_settings.return_value.DEFAULT_REASONING_EFFORT = "medium"
            await service.generate_itineraries("prompt", 1)

        call_args = provider.generate_itineraries.call_args
        assert call_args[0][3] == "medium"

    async def test_ai_input_error_not_retried(self) -> None:
        """AIInputError must fail fast — no retry loop."""
        input_err = AIInputError("Bad destination", "Try Paris", "destination")
        provider = AsyncMock()
        provider.generate_itineraries.side_effect = input_err
        service = AIService(provider=provider)

        with patch("asyncio.sleep") as mock_sleep, pytest.raises(AIInputError):
            await service.generate_itineraries("prompt", 1)

        # Called exactly once — no retries
        provider.generate_itineraries.assert_called_once()
        # No sleep between attempts
        mock_sleep.assert_not_called()

    async def test_calls_list_forwarded_to_provider(self) -> None:
        """If this seam breaks, prod silently writes zero ai_call_logs rows."""
        provider = AsyncMock()
        provider.generate_itineraries.return_value = _make_response()
        service = AIService(provider=provider)
        calls: list = []

        await service.generate_itineraries("prompt", 1, calls=calls)

        assert provider.generate_itineraries.call_args.kwargs["calls"] is calls
