import json

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.participant import Participant
from app.models.preference import Preference
from app.models.trip import Trip
from app.schemas.preference import PreferenceCreate


async def access_trip_by_code(
    trip_code: str, pin: str, db: AsyncSession
) -> Participant:
    result = await db.execute(select(Trip).where(Trip.trip_code == trip_code))
    trip = result.scalar_one_or_none()
    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
        )
    if trip.pin != pin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid PIN"
        )

    result = await db.execute(select(Participant).where(Participant.trip_id == trip.id))
    participant = result.scalars().first()
    return participant


async def get_participant_by_token(token: str, db: AsyncSession) -> Participant:
    result = await db.execute(select(Participant).where(Participant.token == token))
    participant = result.scalar_one_or_none()
    if participant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found"
        )
    return participant


async def submit_preferences(
    token: str,
    payload: PreferenceCreate,
    db: AsyncSession,
    background_tasks: BackgroundTasks | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> Preference:
    participant = await get_participant_by_token(token, db)

    result = await db.execute(
        select(Preference).where(Preference.participant_id == participant.id)
    )
    pref = result.scalar_one_or_none()

    tags_json = (
        json.dumps(payload.activity_tags) if payload.activity_tags is not None else None
    )

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
            activity_tags=tags_json,
        )
        db.add(pref)
    else:
        pref.preferred_start_date = payload.preferred_start_date
        pref.preferred_end_date = payload.preferred_end_date
        pref.budget_min = payload.budget_min
        pref.budget_max = payload.budget_max
        pref.currency = payload.currency
        pref.interests = payload.interests
        pref.activity_tags = tags_json

    participant.preferences_submitted = True

    await db.commit()
    await db.refresh(pref)

    # Auto-trigger generation if all participants have submitted
    if background_tasks is not None and session_factory is not None:
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
    from app.services.generation import run_generation  # avoid circular import

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

    # All submitted — check trip status allows triggering
    trip_result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = trip_result.scalar_one_or_none()
    if trip is None or trip.status not in ("CREATED", "COLLECTING_PREFERENCES"):
        return

    trip.status = "GENERATING"
    await db.commit()

    background_tasks.add_task(run_generation, trip_id, session_factory)
