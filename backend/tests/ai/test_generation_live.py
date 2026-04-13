"""Live AI generation tests — require real API credentials.

Run with: uv run pytest tests/ai -m live -v -s
These tests consume real API credits and are NOT run in CI.

Each class shares one API call via a module-scoped fixture to minimise credit usage.
"""

from __future__ import annotations

import json

import pytest

from app.schemas.itinerary import AIGenerationResponse
from app.services.ai.groq import GroqProvider
from app.services.ai.json_utils import AIInputError
from app.services.ai.service import AIService
from app.services.generation import ITINERARY_PROMPT_V2

_OPEN_DESTINATION = "DESTINATION: Open — suggest the best fit for this group"


def _build_minimal_prompt(
    num_options: int = 1,
    destination_constraint: str = _OPEN_DESTINATION,
) -> str:
    """Minimal rendered prompt for live testing — no DB needed."""
    return ITINERARY_PROMPT_V2.format(
        num_options=num_options,
        trip_duration_days=5,
        trip_title="Live Test Trip",
        proposed_dates="2025-09-01 to 2025-09-06",
        destination_constraint=destination_constraint,
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


# ---------------------------------------------------------------------------
# Module-scoped fixture — one API call shared by TestHuggingFaceLive AND
# TestPromptV2Compliance (both exercise the same happy-path response).
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
async def hf_response() -> tuple[AIGenerationResponse, str]:
    """Single HuggingFace API call reused across all happy-path tests."""
    service = AIService.from_settings()
    prompt = _build_minimal_prompt(num_options=1)
    response, provider = await service.generate_itineraries(prompt, num_options=1)

    # Print raw AI output so it's visible in pytest -s output
    print("\n\n=== AI RESPONSE (HuggingFace) ===")
    print(f"Provider : {provider}")
    print(f"Destination: {response.options[0].destination_name}")
    print(json.dumps(response.options[0].model_dump(), indent=2, ensure_ascii=False))
    print("=================================\n")

    return response, provider


# ---------------------------------------------------------------------------
# Happy-path tests — basic response shape
# ---------------------------------------------------------------------------


@pytest.mark.live
class TestHuggingFaceLive:
    async def test_generate_returns_valid_response(
        self, hf_response: tuple[AIGenerationResponse, str]
    ) -> None:
        """Calls real HF API — requires HF_API_TOKEN in .env."""
        response, provider = hf_response
        assert isinstance(response, AIGenerationResponse)
        assert len(response.options) == 1
        assert provider == "huggingface"

    async def test_each_option_has_required_fields(
        self, hf_response: tuple[AIGenerationResponse, str]
    ) -> None:
        response, _ = hf_response
        for option in response.options:
            assert option.destination_name
            assert option.destination_description
            assert option.total_estimated_budget > 0
            assert option.currency
            assert option.match_reasoning
            assert len(option.highlights) >= 1
            assert len(option.daily_itinerary) >= 1

    async def test_each_day_has_activities(
        self, hf_response: tuple[AIGenerationResponse, str]
    ) -> None:
        response, _ = hf_response
        for option in response.options:
            for day in option.daily_itinerary:
                assert day.day_number >= 1
                assert day.title
                assert len(day.activities) >= 1
                for activity in day.activities:
                    assert activity.title
                    assert activity.description


# ---------------------------------------------------------------------------
# V2 prompt compliance tests — strict rule enforcement
# ---------------------------------------------------------------------------


@pytest.mark.live
class TestPromptV2Compliance:
    async def test_each_day_has_exactly_four_activities(
        self, hf_response: tuple[AIGenerationResponse, str]
    ) -> None:
        """V2 prompt instructs: each day must have exactly 4 activities."""
        response, _ = hf_response
        option = response.options[0]
        assert len(option.daily_itinerary) == 5, (
            f"Expected 5 days, got {len(option.daily_itinerary)}"
        )
        for day in option.daily_itinerary:
            assert len(day.activities) == 4, (
                f"Day {day.day_number} ({day.title!r}): "
                f"expected 4 activities, got {len(day.activities)}"
            )

    async def test_activity_titles_avoid_banned_words(
        self, hf_response: tuple[AIGenerationResponse, str]
    ) -> None:
        """V2 prompt bans AI-sounding filler words."""
        banned = {
            "nestled",
            "vibrant",
            "bustling",
            "hidden gem",
            "a testament to",
            "boasts",
            "delve",
            "tapestry",
            "unwind",
            "indulge",
            "immerse yourself",
        }
        response, _ = hf_response
        violations: list[str] = []
        for option in response.options:
            for day in option.daily_itinerary:
                for activity in day.activities:
                    text = f"{activity.title} {activity.description}".lower()
                    for word in banned:
                        if word in text:
                            violations.append(
                                f"Day {day.day_number} activity {activity.title!r} "
                                f"contains banned word {word!r}"
                            )
        assert not violations, "Banned words found:\n" + "\n".join(violations)


# ---------------------------------------------------------------------------
# Error envelope tests — bad input detection
# ---------------------------------------------------------------------------


@pytest.mark.live
class TestErrorEnvelopeLive:
    async def test_nonsense_destination_raises_ai_input_error(self) -> None:
        """AI should detect a nonsense destination and return an error envelope."""
        service = AIService.from_settings()
        prompt = _build_minimal_prompt(
            num_options=1,
            destination_constraint="DESTINATION: xxxxnotaplace123",
        )

        with pytest.raises(AIInputError) as exc_info:
            await service.generate_itineraries(prompt, num_options=1)

        err = exc_info.value
        print("\n\n=== AI ERROR ENVELOPE ===")
        print(f"field     : {err.field}")
        print(f"message   : {err.ai_message}")
        print(f"suggestion: {err.suggestion}")
        print("=========================\n")

        assert err.field == "destination", (
            f"Expected field='destination', got {err.field!r}"
        )
        assert err.ai_message, "ai_message should be non-empty"
        assert err.suggestion, (
            "suggestion should be non-empty (AI should name alternatives)"
        )

    @pytest.mark.xfail(reason="LLMs inconsistently detect date contradictions")
    async def test_contradictory_dates_raises_ai_input_error(self) -> None:
        """AI may detect end-before-start dates as invalid input."""
        service = AIService.from_settings()
        prompt = ITINERARY_PROMPT_V2.format(
            num_options=1,
            trip_duration_days=0,
            trip_title="Impossible Trip",
            proposed_dates="2025-01-01 to 2024-12-25",
            destination_constraint=_OPEN_DESTINATION,
            participant_count=1,
            preferences_block=(
                "Participant 1:\n"
                "  - Dates: 2025-01-01 to 2024-12-25\n"
                "  - Budget: 500 - 1500 USD\n"
                "  - Interests: beaches\n"
                "  - Activity tags: beach"
            ),
        )

        with pytest.raises(AIInputError) as exc_info:
            await service.generate_itineraries(prompt, num_options=1)

        err = exc_info.value
        assert err.field in {"dates", "general"}


# ---------------------------------------------------------------------------
# Groq fallback test
# ---------------------------------------------------------------------------


@pytest.mark.live
class TestGroqLive:
    async def test_groq_provider_generates_valid_response(self) -> None:
        """Directly tests Groq provider — requires GROQ_API_KEY in .env."""
        from app.core.config import get_settings

        settings = get_settings()
        if not settings.GROQ_API_KEY:
            pytest.skip("GROQ_API_KEY not set")

        provider = GroqProvider(api_key=settings.GROQ_API_KEY)
        prompt = _build_minimal_prompt(num_options=1)
        response, provider_name = await provider.generate_itineraries(
            prompt, num_options=1, model=""
        )

        print("\n\n=== AI RESPONSE (Groq) ===")
        print(f"Provider   : {provider_name}")
        print(f"Destination: {response.options[0].destination_name}")
        print(
            json.dumps(response.options[0].model_dump(), indent=2, ensure_ascii=False)
        )
        print("==========================\n")

        assert isinstance(response, AIGenerationResponse)
        assert len(response.options) == 1
        assert provider_name == "groq"
