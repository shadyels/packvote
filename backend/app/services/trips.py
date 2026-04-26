import asyncio
import random
import secrets
import string

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_call_log import AICallLog
from app.models.itinerary import Itinerary
from app.models.participant import Participant
from app.models.preference import Preference
from app.models.trip import Trip
from app.models.user import User
from app.models.vote import Vote
from app.models.vote_round import VoteRound
from app.schemas.trip import InvitedTripSummary, TripCreate, TripSummary, TripUpdate
from app.services.email.brevo import EmailService

_ALPHANUM = string.ascii_uppercase + string.digits


def _generate_trip_code() -> str:
    return "".join(random.choices(_ALPHANUM, k=8))


def _generate_pin() -> str:
    return "".join(random.choices(string.digits, k=4))


def _next_unique_pin(used: set[str]) -> str:
    pin = _generate_pin()
    while pin in used:
        pin = _generate_pin()
    used.add(pin)
    return pin


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
    creator_result = await db.execute(select(User).where(User.id == creator_id))
    creator = creator_result.scalar_one_or_none()
    if creator is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authenticated user record not found",
        )

    trip_code = await _unique_trip_code(db)

    trip = Trip(
        trip_code=trip_code,
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

    # Dedupe: drop the creator's email from the invite list
    invite_emails = [
        e for e in payload.participant_emails if e.lower() != creator.email.lower()
    ]

    # Batch lookup users by lowercased email to link user_id on participant rows
    lowered = [e.lower() for e in invite_emails]
    email_to_user_id: dict[str, int] = {}
    if lowered:
        user_rows = (
            await db.execute(
                select(User.id, func.lower(User.email)).where(
                    func.lower(User.email).in_(lowered)
                )
            )
        ).all()
        email_to_user_id = {email: uid for uid, email in user_rows}

    participants: list[Participant] = []
    used_pins: set[str] = set()
    for email in invite_emails:
        token = secrets.token_urlsafe(32)
        participant = Participant(
            trip_id=trip.id,
            email=email,
            token=token,
            pin=_next_unique_pin(used_pins),
            user_id=email_to_user_id.get(email.lower()),
        )
        db.add(participant)
        participants.append(participant)

    # Insert the creator as a participant (never emailed, preferences pre-submitted)
    creator_participant = Participant(
        trip_id=trip.id,
        email=creator.email,
        name=creator.full_name,
        token=secrets.token_urlsafe(32),
        pin=_next_unique_pin(used_pins),
        user_id=creator.id,
        preferences_submitted=True,
    )
    db.add(creator_participant)

    await db.commit()
    await db.refresh(trip)

    # Fire-and-forget — email failure must not roll back the trip
    # creator_participant is intentionally excluded from this list
    asyncio.gather(
        *[
            email_service.send_invitation(
                to_email=p.email,
                participant_name=p.name,
                trip_title=trip.title,
                trip_code=trip.trip_code,
                pin=p.pin,
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


async def list_invited_trips_for_user(
    user_id: int, db: AsyncSession
) -> list[InvitedTripSummary]:
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
            Participant.token.label("participant_token"),
        )
        .join(Participant, Participant.trip_id == Trip.id)
        .where(
            Participant.user_id == user_id,
            Trip.creator_id != user_id,
        )
        .order_by(Trip.created_at.desc())
    )
    result = await db.execute(stmt)
    summaries = []
    for trip, participant_count, preferences_submitted_count, participant_token in result.all():
        summaries.append(
            InvitedTripSummary.model_validate(
                {
                    "id": trip.id,
                    "trip_code": trip.trip_code,
                    "title": trip.title,
                    "destination": trip.destination,
                    "status": trip.status,
                    "participant_count": participant_count,
                    "preferences_submitted_count": preferences_submitted_count,
                    "created_at": trip.created_at,
                    "participant_token": participant_token,
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


_EDITABLE_STATUSES = ("CREATED", "COLLECTING_PREFERENCES", "GENERATION_FAILED")


async def update_trip(
    trip_id: int, user_id: int, payload: TripUpdate, db: AsyncSession
) -> Trip:
    trip = await get_trip(trip_id, user_id, db)
    if trip.status not in _EDITABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot edit a trip with status '{trip.status}'",
        )
    if payload.title is not None:
        trip.title = payload.title
    if payload.destination is not None:
        trip.destination = payload.destination
    if payload.proposed_start_date is not None:
        trip.proposed_start_date = payload.proposed_start_date
    if payload.proposed_end_date is not None:
        trip.proposed_end_date = payload.proposed_end_date
    if payload.num_options is not None:
        trip.num_options = payload.num_options
    if payload.notes is not None:
        trip.notes = payload.notes
    await db.commit()
    await db.refresh(trip)
    return trip


async def list_participants_for_trip(
    trip_id: int, user_id: int, db: AsyncSession
) -> list[dict]:
    trip = await get_trip(trip_id, user_id, db)

    has_voted_sq = (
        select(Vote.id)
        .where(
            Vote.trip_id == trip_id,
            Vote.participant_id == Participant.id,
            Vote.iteration_number == trip.current_iteration,
        )
        .correlate(Participant)
        .exists()
        .label("has_voted_current_iteration")
    )

    result = await db.execute(
        select(Participant, has_voted_sq)
        .where(Participant.trip_id == trip_id)
        .order_by(Participant.created_at)
    )

    return [
        {
            "id": p.id,
            "trip_id": p.trip_id,
            "email": p.email,
            "name": p.name,
            "preferences_submitted": p.preferences_submitted,
            "has_voted_current_iteration": bool(has_voted),
            "created_at": p.created_at,
        }
        for p, has_voted in result.all()
    ]


async def delete_trip(trip_id: int, user_id: int, db: AsyncSession) -> None:
    trip = await get_trip(trip_id, user_id, db)
    if trip.status == "GENERATING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a trip while generation is in progress",
        )

    # Delete child rows in FK-safe order
    await db.execute(delete(VoteRound).where(VoteRound.trip_id == trip_id))
    await db.execute(delete(Vote).where(Vote.trip_id == trip_id))
    await db.execute(delete(Preference).where(Preference.trip_id == trip_id))
    await db.execute(delete(AICallLog).where(AICallLog.trip_id == trip_id))

    # Break circular FK (trip.winner_itinerary_id -> itineraries.id) before deleting itineraries
    trip.winner_itinerary_id = None
    await db.flush()

    await db.execute(delete(Itinerary).where(Itinerary.trip_id == trip_id))
    await db.execute(delete(Participant).where(Participant.trip_id == trip_id))
    await db.delete(trip)
    await db.commit()


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
