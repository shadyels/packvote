"""Live AI generation tests — require real API credentials.

Run with: uv run pytest tests/ai -m live -v
These tests consume real API credits and are NOT run in CI.
"""

from __future__ import annotations

import pytest

from app.schemas.itinerary import AIGenerationResponse
from app.services.ai.groq import GroqProvider
from app.services.ai.service import AIService
from app.services.generation import ITINERARY_PROMPT_V1


def _build_minimal_prompt(num_options: int = 2) -> str:
    """Minimal rendered prompt for live testing — no DB needed."""
    return ITINERARY_PROMPT_V1.format(
        num_options=num_options,
        trip_duration_days=5,
        trip_title="Live Test Trip",
        proposed_dates="2025-09-01 to 2025-09-06",
        destination_constraint="DESTINATION: Open — suggest the best fit for this group",
        participant_count=2,
        preferences_block=(
            "Participant 1:\n"
            "  - Dates: 2025-09-01 to 2025-09-06\n"
            "  - Budget: 500 - 1500 USD\n"
            "  - Interests: beaches, local cuisine\n"
            "  - Activity tags: beach, food_tour\n\n"
            "Participant 2:\n"
            "  - Dates: 2025-09-01 to 2025-09-06\n"
            "  - Budget: 800 - 2000 USD\n"
            "  - Interests: history, architecture\n"
            "  - Activity tags: museums, walking_tours"
        ),
    )


@pytest.mark.live
class TestHuggingFaceLive:
    async def test_generate_returns_valid_response(self):
        """Calls real HF API — requires HF_API_TOKEN in .env."""
        service = AIService.from_settings()
        prompt = _build_minimal_prompt(num_options=2)
        response, provider = await service.generate_itineraries(prompt, num_options=2)

        assert isinstance(response, AIGenerationResponse)
        assert len(response.options) == 2
        assert provider == "huggingface"

    async def test_each_option_has_required_fields(self):
        service = AIService.from_settings()
        prompt = _build_minimal_prompt(num_options=2)
        response, _ = await service.generate_itineraries(prompt, num_options=2)

        for option in response.options:
            assert option.destination_name
            assert option.destination_description
            assert option.total_estimated_budget > 0
            assert option.currency
            assert option.match_reasoning
            assert len(option.highlights) >= 1
            assert len(option.daily_itinerary) >= 1

    async def test_each_day_has_activities(self):
        service = AIService.from_settings()
        prompt = _build_minimal_prompt(num_options=2)
        response, _ = await service.generate_itineraries(prompt, num_options=2)

        for option in response.options:
            for day in option.daily_itinerary:
                assert day.day_number >= 1
                assert day.title
                assert len(day.activities) >= 1
                for activity in day.activities:
                    assert activity.title
                    assert activity.description


@pytest.mark.live
class TestGroqLive:
    async def test_groq_provider_generates_valid_response(self):
        """Directly tests Groq provider — requires GROQ_API_KEY in .env."""
        from app.core.config import get_settings

        settings = get_settings()
        if not settings.GROQ_API_KEY:
            pytest.skip("GROQ_API_KEY not set")

        provider = GroqProvider(api_key=settings.GROQ_API_KEY)
        prompt = _build_minimal_prompt(num_options=2)
        response, provider_name = await provider.generate_itineraries(
            prompt, num_options=2, model=""
        )

        assert isinstance(response, AIGenerationResponse)
        assert len(response.options) == 2
        assert provider_name == "groq"
