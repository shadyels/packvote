from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.itinerary import Itinerary as ItineraryModel
from app.models.participant import Participant
from app.models.preference import Preference
from app.models.trip import Trip, TripStatus
from app.models.vote import Vote
from app.schemas.participant import ParticipantTripView
from app.schemas.preference import PreferenceCreate
from app.services import generation
from app.services.generation import start_generation
from app.services.rate_limit import SlidingWindow

# ponytail: in-process only; resets on restart and is per worker. Upgrade path:
# DB/Redis-backed failure counter.
_pin_windows: dict[int, SlidingWindow] = {}


async def access_trip_by_code(
    trip_code: str, pin: str, db: AsyncSession
) -> Participant:
    invalid = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Invalid trip code or PIN"
    )
    trip = (
        await db.execute(select(Trip).where(Trip.trip_code == trip_code))
    ).scalar_one_or_none()
    if trip is None:
        raise invalid  # unknown codes are not recorded
    window = _pin_windows.setdefault(trip.id, SlidingWindow(10, 86400))
    if not window.allowed():
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Try again later.",
        )
    participant = (
        await db.execute(
            select(Participant).where(
                Participant.trip_id == trip.id, Participant.pin == pin
            )
        )
    ).scalar_one_or_none()
    if participant is None:
        window.hit()
        raise invalid
    return participant


async def get_participant_by_token(token: str, db: AsyncSession) -> Participant:
    result = await db.execute(select(Participant).where(Participant.token == token))
    participant = result.scalar_one_or_none()
    if participant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found"
        )
    return participant


async def get_participant_trip_view(
    token: str, db: AsyncSession
) -> ParticipantTripView:
    """Return all trip data needed for the participant-facing trip page."""
    from app.schemas.itinerary import ItineraryResponse
    from app.schemas.participant import (
        ParticipantBrief,
        ParticipantResponse,
        TripPublicInfo,
    )
    from app.services.voting.service import compute_results

    participant = await get_participant_by_token(token, db)

    trip_result = await db.execute(select(Trip).where(Trip.id == participant.trip_id))
    trip = trip_result.scalar_one_or_none()
    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
        )

    # All participants for the trip (names/status only — no emails exposed)
    all_participants_result = await db.execute(
        select(Participant).where(Participant.trip_id == trip.id)
    )
    all_participants = all_participants_result.scalars().all()
    participant_briefs = [
        ParticipantBrief(
            id=p.id,
            name=p.name,
            preferences_submitted=p.preferences_submitted,
        )
        for p in all_participants
    ]

    # Itineraries for current iteration (only relevant during/after voting)
    itineraries: list[ItineraryModel] = []
    show_itinerary_statuses = {"VOTING", "FINALIZED"}
    if trip.status in show_itinerary_statuses:
        itin_result = await db.execute(
            select(ItineraryModel).where(
                ItineraryModel.trip_id == trip.id,
                ItineraryModel.iteration_number == trip.current_iteration,
            )
        )
        itineraries = list(itin_result.scalars().all())

        # For FINALIZED, also include the winner if it's from a different iteration
        if trip.status == "FINALIZED" and trip.winner_itinerary_id:
            winner_ids = {it.id for it in itineraries}
            if trip.winner_itinerary_id not in winner_ids:
                winner_result = await db.execute(
                    select(ItineraryModel).where(
                        ItineraryModel.id == trip.winner_itinerary_id
                    )
                )
                winner = winner_result.scalar_one_or_none()
                if winner:
                    itineraries.append(winner)

    # Voting results (if available)
    voting_results = None
    if trip.status in show_itinerary_statuses:
        voting_results = await compute_results(db, trip)

    # Has this participant already voted in the current iteration?
    vote_result = await db.execute(
        select(Vote).where(
            Vote.trip_id == trip.id,
            Vote.iteration_number == trip.current_iteration,
            Vote.participant_id == participant.id,
        )
    )
    has_voted = vote_result.scalar_one_or_none() is not None

    return ParticipantTripView(
        participant=ParticipantResponse.model_validate(participant).model_copy(
            update={"has_voted_current_iteration": has_voted}
        ),
        trip=TripPublicInfo.model_validate(trip),
        participants=participant_briefs,
        itineraries=[ItineraryResponse.model_validate(it) for it in itineraries],
        voting_results=voting_results,
        has_voted=has_voted,
    )


async def submit_preferences(
    token: str,
    payload: PreferenceCreate,
    db: AsyncSession,
    background_tasks: BackgroundTasks,
    session_factory: async_sessionmaker[AsyncSession],
) -> Preference:
    participant = await get_participant_by_token(token, db)

    result = await db.execute(
        select(Preference).where(Preference.participant_id == participant.id)
    )
    pref = result.scalar_one_or_none()

    if pref is None:
        pref = Preference(
            participant_id=participant.id,
            trip_id=participant.trip_id,
            preferred_start_date=payload.preferred_start_date,
            preferred_end_date=payload.preferred_end_date,
            budget_min=payload.budget_min,
            budget_max=payload.budget_max,
            currency=payload.currency,
            interests=payload.interests,
            activity_tags=payload.activity_tags,
        )
        db.add(pref)
    else:
        pref.preferred_start_date = payload.preferred_start_date
        pref.preferred_end_date = payload.preferred_end_date
        pref.budget_min = payload.budget_min
        pref.budget_max = payload.budget_max
        pref.currency = payload.currency
        pref.interests = payload.interests
        pref.activity_tags = payload.activity_tags

    if payload.name is not None:
        stripped = payload.name.strip()
        if stripped:
            participant.name = stripped
    participant.preferences_submitted = True

    await db.commit()
    await db.refresh(pref)

    # Auto-trigger generation if all participants have submitted
    await _maybe_trigger_generation(
        trip_id=participant.trip_id,
        db=db,
        session_factory=session_factory,
        background_tasks=background_tasks,
    )

    return pref


async def _maybe_trigger_generation(
    trip_id: int,
    db: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
    background_tasks: BackgroundTasks,
) -> None:
    """Auto-trigger generation when all participants have submitted preferences."""
    total_result = await db.execute(
        select(func.count(Participant.id)).where(Participant.trip_id == trip_id)
    )
    total = total_result.scalar_one()

    submitted_result = await db.execute(
        select(func.count(Participant.id)).where(
            Participant.trip_id == trip_id,
            Participant.preferences_submitted.is_(True),
        )
    )
    submitted = submitted_result.scalar_one()

    if total == 0 or submitted < total:
        return

    # All submitted — atomically claim the transition; losers do nothing
    if await start_generation(
        db, trip_id, [TripStatus.CREATED, TripStatus.COLLECTING_PREFERENCES]
    ):
        background_tasks.add_task(generation.run_generation, trip_id, session_factory)
