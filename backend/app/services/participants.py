import json

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.participant import Participant
from app.models.preference import Preference
from app.models.trip import Trip
from app.schemas.preference import PreferenceCreate


async def access_trip_by_code(trip_code: str, pin: str, db: AsyncSession) -> Participant:
    result = await db.execute(select(Trip).where(Trip.trip_code == trip_code))
    trip = result.scalar_one_or_none()
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    if trip.pin != pin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid PIN")

    result = await db.execute(
        select(Participant).where(Participant.trip_id == trip.id)
    )
    participant = result.scalars().first()
    return participant


async def get_participant_by_token(token: str, db: AsyncSession) -> Participant:
    result = await db.execute(select(Participant).where(Participant.token == token))
    participant = result.scalar_one_or_none()
    if participant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")
    return participant


async def submit_preferences(
    token: str,
    payload: PreferenceCreate,
    db: AsyncSession,
) -> Preference:
    participant = await get_participant_by_token(token, db)

    result = await db.execute(
        select(Preference).where(Preference.participant_id == participant.id)
    )
    pref = result.scalar_one_or_none()

    tags_json = json.dumps(payload.activity_tags) if payload.activity_tags is not None else None

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
    return pref
