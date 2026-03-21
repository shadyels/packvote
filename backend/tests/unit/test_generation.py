"""Unit tests for AI itinerary generation service.

All tests use mocked AI — no real API calls.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.participant import Participant
from app.models.preference import Preference
from app.models.trip import Trip
from app.schemas.itinerary import (
    AIGenerationResponse,
    DailyActivity,
    DayItinerary,
    ItineraryOption,
)
from app.services.ai.service import AIService
from app.services.generation import (
    _build_preferences_block,
    _compute_trip_duration,
    _upsert_prompt_template,
    run_generation,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

NOW = datetime(2025, 8, 1, tzinfo=UTC)


def _make_trip(**kwargs) -> Trip:
    defaults = dict(
        id=1,
        trip_code="ABCD1234",
        creator_id=1,
        title="Beach Getaway",
        destination=None,
        proposed_start_date=None,
        proposed_end_date=None,
        num_options=3,
        status="GENERATING",
        current_iteration=0,
        max_iterations=10,
        notes=None,
        created_at=NOW,
    )
    defaults.update(kwargs)
    t = Trip(**defaults)
    return t


def _make_pref(**kwargs) -> Preference:
    defaults = dict(
        id=1,
        participant_id=1,
        trip_id=1,
        preferred_start_date=None,
        preferred_end_date=None,
        budget_min=500.0,
        budget_max=1500.0,
        currency="USD",
        interests="beaches, local food",
        activity_tags='["beach", "snorkeling"]',
        submitted_at=NOW,
    )
    defaults.update(kwargs)
    return Preference(**defaults)


def _make_itinerary_option(destination: str = "Barcelona") -> ItineraryOption:
    return ItineraryOption(
        destination_name=destination,
        destination_description="A vibrant city with amazing beaches.",
        daily_itinerary=[
            DayItinerary(
                day_number=1,
                title="Arrival day",
                activities=[
                    DailyActivity(
                        time="10:00",
                        title="Check in",
                        description="Settle into the hotel.",
                        estimated_cost=None,
                    )
                ],
                estimated_cost=None,
            )
        ],
        total_estimated_budget=2000.0,
        currency="EUR",
        match_reasoning="Great for beach lovers with an interest in local food.",
        highlights=["Sagrada Familia", "La Barceloneta Beach", "La Boqueria Market"],
    )


def _mock_ai_response(num_options: int = 3) -> tuple[AIGenerationResponse, str]:
    options = [
        _make_itinerary_option(f"Destination {i + 1}") for i in range(num_options)
    ]
    return AIGenerationResponse(options=options), "huggingface"


# ---------------------------------------------------------------------------
# _build_preferences_block
# ---------------------------------------------------------------------------


class TestBuildPreferencesBlock:
    def test_empty_returns_no_preferences_message(self):
        result = _build_preferences_block([])
        assert "No preferences submitted" in result

    def test_single_participant_renders_all_fields(self):
        pref = _make_pref(
            preferred_start_date=datetime(2025, 8, 1, tzinfo=UTC),
            preferred_end_date=datetime(2025, 8, 10, tzinfo=UTC),
        )
        result = _build_preferences_block([pref])
        assert "Participant 1" in result
        assert "2025-08-01" in result
        assert "2025-08-10" in result
        assert "500.0" in result
        assert "1500.0" in result
        assert "USD" in result
        assert "beaches" in result
        assert "beach" in result
        assert "snorkeling" in result

    def test_flexible_dates_when_no_dates(self):
        pref = _make_pref()
        result = _build_preferences_block([pref])
        assert "flexible" in result

    def test_multiple_participants_numbered(self):
        prefs = [_make_pref(id=i, participant_id=i) for i in range(1, 4)]
        result = _build_preferences_block(prefs)
        assert "Participant 1" in result
        assert "Participant 2" in result
        assert "Participant 3" in result

    def test_invalid_activity_tags_json_ignored(self):
        pref = _make_pref(activity_tags="not-valid-json")
        result = _build_preferences_block([pref])
        assert "Participant 1" in result  # still renders; tags are just skipped


# ---------------------------------------------------------------------------
# _compute_trip_duration
# ---------------------------------------------------------------------------


class TestComputeTripDuration:
    def test_uses_trip_dates_when_present(self):
        trip = _make_trip(
            proposed_start_date=datetime(2025, 8, 1, tzinfo=UTC),
            proposed_end_date=datetime(2025, 8, 10, tzinfo=UTC),
        )
        assert _compute_trip_duration(trip, []) == 9

    def test_uses_median_participant_duration_when_no_trip_dates(self):
        trip = _make_trip()
        prefs = [
            _make_pref(
                id=1,
                preferred_start_date=datetime(2025, 8, 1, tzinfo=UTC),
                preferred_end_date=datetime(2025, 8, 8, tzinfo=UTC),  # 7 days
            ),
            _make_pref(
                id=2,
                preferred_start_date=datetime(2025, 8, 1, tzinfo=UTC),
                preferred_end_date=datetime(2025, 8, 11, tzinfo=UTC),  # 10 days
            ),
            _make_pref(
                id=3,
                preferred_start_date=datetime(2025, 8, 1, tzinfo=UTC),
                preferred_end_date=datetime(2025, 8, 6, tzinfo=UTC),  # 5 days
            ),
        ]
        result = _compute_trip_duration(trip, prefs)
        assert result == 7  # median of [5, 7, 10]

    def test_fallback_to_7_when_no_dates_anywhere(self):
        trip = _make_trip()
        assert _compute_trip_duration(trip, []) == 7

    def test_fallback_to_7_when_preferences_have_no_dates(self):
        trip = _make_trip()
        prefs = [_make_pref()]  # no dates on preference
        assert _compute_trip_duration(trip, prefs) == 7


# ---------------------------------------------------------------------------
# _upsert_prompt_template
# ---------------------------------------------------------------------------


class TestUpsertPromptTemplate:
    async def test_creates_template_on_first_call(self, db: AsyncSession):
        from sqlalchemy import select

        from app.models.prompt_template import PromptTemplate

        template = await _upsert_prompt_template(db)
        assert template.id is not None
        assert template.name == "itinerary_generation"
        assert template.version == "v1"
        assert template.is_active is True
        assert "[SYSTEM]" in template.template_text

        # Verify it's in the DB
        result = await db.execute(
            select(PromptTemplate).where(PromptTemplate.name == "itinerary_generation")
        )
        assert result.scalar_one_or_none() is not None

    async def test_returns_existing_on_second_call(self, db: AsyncSession):
        template1 = await _upsert_prompt_template(db)
        await db.commit()
        template2 = await _upsert_prompt_template(db)
        assert template1.id == template2.id

    async def test_idempotent_no_duplicates(self, db: AsyncSession):
        from sqlalchemy import func, select

        from app.models.prompt_template import PromptTemplate

        await _upsert_prompt_template(db)
        await db.commit()
        await _upsert_prompt_template(db)
        await db.commit()

        result = await db.execute(
            select(func.count(PromptTemplate.id)).where(
                PromptTemplate.name == "itinerary_generation",
                PromptTemplate.version == "v1",
            )
        )
        count = result.scalar_one()
        assert count == 1


# ---------------------------------------------------------------------------
# run_generation — integration tests with mocked AI
# ---------------------------------------------------------------------------


@pytest.fixture
async def trip_with_preferences(db: AsyncSession):
    """Create a trip + participants + preferences in the test DB."""
    import bcrypt

    from app.models.user import User

    user = User(
        email=f"creator_{secrets.token_hex(4)}@test.com",
        hashed_password=bcrypt.hashpw(b"password", bcrypt.gensalt()).decode(),
        full_name="Test Creator",
    )
    db.add(user)
    await db.flush()

    trip = Trip(
        trip_code=secrets.token_hex(4).upper()[:8],
        creator_id=user.id,
        title="Group Adventure",
        num_options=2,
        status="GENERATING",
        current_iteration=0,
        max_iterations=10,
    )
    db.add(trip)
    await db.flush()

    for i in range(2):
        participant = Participant(
            trip_id=trip.id,
            email=f"p{i}@test.com",
            token=secrets.token_urlsafe(32),
            pin=str(i + 1).zfill(4),
            preferences_submitted=True,
        )
        db.add(participant)
        await db.flush()

        pref = Preference(
            participant_id=participant.id,
            trip_id=trip.id,
            budget_min=500.0,
            budget_max=2000.0,
            currency="USD",
            interests="beaches and hiking",
            activity_tags='["beach", "hiking"]',
        )
        db.add(pref)

    await db.commit()
    return trip


@pytest.fixture
def session_factory_fixture(engine):
    """Return a session factory backed by the test engine."""
    return async_sessionmaker(engine, expire_on_commit=False)


class TestRunGeneration:
    async def test_success_sets_status_voting(
        self, db: AsyncSession, trip_with_preferences: Trip, session_factory_fixture
    ):
        from sqlalchemy import select

        from app.models.trip import Trip as TripModel

        trip_id = trip_with_preferences.id  # save before expire_all
        with patch.object(
            AIService,
            "generate_itineraries",
            new_callable=AsyncMock,
            return_value=_mock_ai_response(num_options=2),
        ):
            await run_generation(trip_id, session_factory_fixture)

        db.expire_all()
        result = await db.execute(select(TripModel).where(TripModel.id == trip_id))
        trip = result.scalar_one()
        assert trip.status == "VOTING"

    async def test_success_creates_correct_number_of_itineraries(
        self, db: AsyncSession, trip_with_preferences: Trip, session_factory_fixture
    ):
        from sqlalchemy import select

        from app.models.itinerary import Itinerary

        trip_id = trip_with_preferences.id
        with patch.object(
            AIService,
            "generate_itineraries",
            new_callable=AsyncMock,
            return_value=_mock_ai_response(num_options=2),
        ):
            await run_generation(trip_id, session_factory_fixture)

        db.expire_all()
        result = await db.execute(select(Itinerary).where(Itinerary.trip_id == trip_id))
        itineraries = result.scalars().all()
        assert len(itineraries) == 2

    async def test_success_increments_current_iteration(
        self, db: AsyncSession, trip_with_preferences: Trip, session_factory_fixture
    ):
        from sqlalchemy import select

        from app.models.trip import Trip as TripModel

        trip_id = trip_with_preferences.id
        with patch.object(
            AIService,
            "generate_itineraries",
            new_callable=AsyncMock,
            return_value=_mock_ai_response(num_options=2),
        ):
            await run_generation(trip_id, session_factory_fixture)

        db.expire_all()
        result = await db.execute(select(TripModel).where(TripModel.id == trip_id))
        trip = result.scalar_one()
        assert trip.current_iteration == 1

    async def test_success_logs_ai_call_valid(
        self, db: AsyncSession, trip_with_preferences: Trip, session_factory_fixture
    ):
        from sqlalchemy import select

        from app.models.ai_call_log import AICallLog

        trip_id = trip_with_preferences.id
        with patch.object(
            AIService,
            "generate_itineraries",
            new_callable=AsyncMock,
            return_value=_mock_ai_response(num_options=2),
        ):
            await run_generation(trip_id, session_factory_fixture)

        db.expire_all()
        result = await db.execute(select(AICallLog).where(AICallLog.trip_id == trip_id))
        log = result.scalar_one_or_none()
        assert log is not None
        assert log.response_valid is True
        assert log.error_message is None

    async def test_failure_resets_status_to_collecting(
        self, db: AsyncSession, trip_with_preferences: Trip, session_factory_fixture
    ):
        from sqlalchemy import select

        from app.models.trip import Trip as TripModel

        trip_id = trip_with_preferences.id
        with patch.object(
            AIService,
            "generate_itineraries",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Provider unavailable"),
        ):
            await run_generation(trip_id, session_factory_fixture)

        db.expire_all()
        result = await db.execute(select(TripModel).where(TripModel.id == trip_id))
        trip = result.scalar_one()
        assert trip.status == "COLLECTING_PREFERENCES"

    async def test_failure_logs_ai_call_invalid(
        self, db: AsyncSession, trip_with_preferences: Trip, session_factory_fixture
    ):
        from sqlalchemy import select

        from app.models.ai_call_log import AICallLog

        trip_id = trip_with_preferences.id
        with patch.object(
            AIService,
            "generate_itineraries",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Provider unavailable"),
        ):
            await run_generation(trip_id, session_factory_fixture)

        db.expire_all()
        result = await db.execute(select(AICallLog).where(AICallLog.trip_id == trip_id))
        log = result.scalar_one_or_none()
        assert log is not None
        assert log.response_valid is False
        assert "Provider unavailable" in log.error_message

    async def test_idempotency_guard_skips_if_not_generating(
        self, db: AsyncSession, trip_with_preferences: Trip, session_factory_fixture
    ):
        from sqlalchemy import select

        from app.models.trip import Trip as TripModel

        # Manually set the trip to a different status
        async with session_factory_fixture() as s:
            result = await s.execute(
                select(TripModel).where(TripModel.id == trip_with_preferences.id)
            )
            t = result.scalar_one()
            t.status = "VOTING"
            await s.commit()

        mock_ai = AsyncMock(return_value=_mock_ai_response(2))
        with patch.object(AIService, "generate_itineraries", mock_ai):
            await run_generation(trip_with_preferences.id, session_factory_fixture)

        mock_ai.assert_not_called()
