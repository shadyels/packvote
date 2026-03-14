import asyncio
import random
import secrets
import string

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_call_log import AICallLog
from app.models.itinerary import Itinerary
from app.models.participant import Participant
from app.models.trip import Trip
from app.schemas.trip import TripCreate, TripSummary
from app.services.email.sendgrid import EmailService

_ALPHANUM = string.ascii_uppercase + string.digits


def _generate_trip_code() -> str:
    return "".join(random.choices(_ALPHANUM, k=8))


def _generate_pin() -> str:
    return "".join(random.choices(string.digits, k=4))


async def _unique_trip_code(db: AsyncSession) -> str:
    for _ in range(10):
        code = _generate_trip_code()
        result = await db.execute(select(Trip).where(Trip.trip_code == code))
        if result.scalar_one_or_none() is None:
            return code
    return _generate_trip_code()


async def create_trip(
    payload: TripCreate,
    creator_id: int,
    db: AsyncSession,
    email_service: EmailService,
) -> Trip:
    trip_code = await _unique_trip_code(db)
    pin = _generate_pin()

    trip = Trip(
        trip_code=trip_code,
        pin=pin,
        creator_id=creator_id,
        title=payload.title,
        destination=payload.destination,
        proposed_start_date=payload.proposed_start_date,
        proposed_end_date=payload.proposed_end_date,
        num_options=payload.num_options,
        notes=payload.notes,
    )
    db.add(trip)

    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        # Extremely rare race on trip_code — retry once with a fresh code
        trip.trip_code = _generate_trip_code()
        db.add(trip)
        await db.flush()

    participants: list[Participant] = []
    for email in payload.participant_emails:
        token = secrets.token_urlsafe(32)
        participant = Participant(trip_id=trip.id, email=email, token=token)
        db.add(participant)
        participants.append(participant)

    await db.commit()
    await db.refresh(trip)

    # Fire-and-forget — email failure must not roll back the trip
    asyncio.gather(
        *[
            email_service.send_invitation(
                to_email=p.email,
                participant_name=p.name,
                trip_title=trip.title,
                trip_code=trip.trip_code,
                pin=trip.pin,
                token=p.token,
            )
            for p in participants
        ],
        return_exceptions=True,
    )

    return trip


async def list_trips_for_user(user_id: int, db: AsyncSession) -> list[TripSummary]:
    participant_count_sq = (
        select(func.count(Participant.id))
        .where(Participant.trip_id == Trip.id)
        .correlate(Trip)
        .scalar_subquery()
    )
    pref_submitted_sq = (
        select(func.count(Participant.id))
        .where(
            Participant.trip_id == Trip.id,
            Participant.preferences_submitted.is_(True),
        )
        .correlate(Trip)
        .scalar_subquery()
    )
    stmt = (
        select(
            Trip,
            participant_count_sq.label("participant_count"),
            pref_submitted_sq.label("preferences_submitted_count"),
        )
        .where(Trip.creator_id == user_id)
        .order_by(Trip.created_at.desc())
    )
    result = await db.execute(stmt)
    summaries = []
    for trip, participant_count, preferences_submitted_count in result.all():
        summaries.append(
            TripSummary.model_validate(
                {
                    "id": trip.id,
                    "trip_code": trip.trip_code,
                    "title": trip.title,
                    "destination": trip.destination,
                    "status": trip.status,
                    "participant_count": participant_count,
                    "preferences_submitted_count": preferences_submitted_count,
                    "created_at": trip.created_at,
                }
            )
        )
    return summaries


async def get_trip(trip_id: int, user_id: int, db: AsyncSession) -> Trip:
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()
    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
        )
    if trip.creator_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )
    return trip


async def list_participants_for_trip(
    trip_id: int, user_id: int, db: AsyncSession
) -> list[Participant]:
    await get_trip(trip_id, user_id, db)
    result = await db.execute(
        select(Participant)
        .where(Participant.trip_id == trip_id)
        .order_by(Participant.created_at)
    )
    return list(result.scalars().all())


async def list_itineraries_for_trip(
    trip_id: int, user_id: int, db: AsyncSession
) -> list[Itinerary]:
    await get_trip(trip_id, user_id, db)
    result = await db.execute(
        select(Itinerary)
        .where(Itinerary.trip_id == trip_id)
        .order_by(Itinerary.iteration_number, Itinerary.id)
    )
    return list(result.scalars().all())


async def list_ai_logs_for_trip(
    trip_id: int, user_id: int, db: AsyncSession
) -> list[AICallLog]:
    await get_trip(trip_id, user_id, db)
    result = await db.execute(
        select(AICallLog)
        .where(AICallLog.trip_id == trip_id)
        .order_by(AICallLog.created_at.desc())
    )
    return list(result.scalars().all())
