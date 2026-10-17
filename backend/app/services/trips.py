import asyncio
import random
import secrets
import string
from datetime import UTC, datetime

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.itinerary import Itinerary
from app.models.participant import Participant
from app.models.trip import Trip, TripStatus
from app.models.user import User
from app.models.vote import Vote
from app.schemas._limits import max_trip_days
from app.schemas.trip import InvitedTripSummary, TripCreate, TripSummary, TripUpdate
from app.services import generation
from app.services.email.brevo import EmailService
from app.services.generation import start_generation

_ALPHANUM = string.ascii_uppercase + string.digits


def _generate_trip_code() -> str:
    return "".join(secrets.choice(_ALPHANUM) for _ in range(8))


def _distinct_pins(n: int) -> list[str]:
    """n distinct 4-digit PINs (the (trip_id, pin) pair is unique)."""
    return [f"{p:04d}" for p in random.SystemRandom().sample(range(10_000), n)]


async def send_invitations(
    email_service: EmailService,
    trip_title: str,
    trip_code: str,
    invitees: list[dict[str, str | None]],
) -> None:
    """Background task: best-effort invitation emails from snapshotted values."""
    await asyncio.gather(
        *[
            email_service.send_invitation(
                to_email=i["email"],
                participant_name=i["name"],
                trip_title=trip_title,
                trip_code=trip_code,
                pin=i["pin"],
                token=i["token"],
            )
            for i in invitees
        ],
        return_exceptions=True,
    )


async def create_trip(
    payload: TripCreate,
    creator_id: int,
    db: AsyncSession,
    email_service: EmailService,
    background_tasks: BackgroundTasks,
) -> Trip:
    creator_result = await db.execute(select(User).where(User.id == creator_id))
    creator = creator_result.scalar_one_or_none()
    if creator is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authenticated user record not found",
        )

    # ponytail: no pre-check/retry on trip_code. 36^8 codes make a collision
    # negligible; if it ever happens the unique constraint raises IntegrityError
    # -> 500. Upgrade path: retry on IntegrityError with a fresh code.
    trip = Trip(
        trip_code=_generate_trip_code(),
        creator_id=creator_id,
        title=payload.title,
        destination=payload.destination,
        proposed_start_date=payload.proposed_start_date,
        proposed_end_date=payload.proposed_end_date,
        num_options=payload.num_options,
        notes=payload.notes,
    )
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

    # Participants are only ever created here (none are added later), so
    # distinct PINs within this batch are enough.
    pins = iter(_distinct_pins(len(invite_emails) + 1))
    participants: list[Participant] = []
    for email in invite_emails:
        token = secrets.token_urlsafe(32)
        participant = Participant(
            trip_id=trip.id,
            email=email,
            token=token,
            pin=next(pins),
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
        pin=next(pins),
        user_id=creator.id,
        preferences_submitted=True,
    )
    db.add(creator_participant)

    await db.commit()
    await db.refresh(trip)

    # Sent after the response; email failure must not affect the trip.
    # The creator's participant row is intentionally excluded.
    background_tasks.add_task(
        send_invitations,
        email_service,
        trip.title,
        trip.trip_code,
        [
            {"email": p.email, "name": p.name, "pin": p.pin, "token": p.token}
            for p in participants
        ],
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
    for (
        trip,
        participant_count,
        preferences_submitted_count,
        participant_token,
    ) in result.all():
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


_EDITABLE_STATUSES = (
    TripStatus.CREATED,
    TripStatus.COLLECTING_PREFERENCES,
    TripStatus.GENERATION_FAILED,
)


def _as_utc(dt: datetime) -> datetime:
    # SQLite hands back naive datetimes; Postgres/pydantic give aware ones.
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


async def update_trip(
    trip_id: int, user_id: int, payload: TripUpdate, db: AsyncSession
) -> Trip:
    trip = await get_trip(trip_id, user_id, db)
    if trip.status not in _EDITABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot edit a trip with status '{trip.status}'",
        )
    # exclude_none keeps the previous semantics: None means "leave unchanged"
    # (a field cannot be cleared via PATCH).
    changes = payload.model_dump(exclude_none=True)
    merged = {
        f: changes.get(f, getattr(trip, f))
        for f in ("proposed_start_date", "proposed_end_date", "num_options")
    }
    start, end = merged["proposed_start_date"], merged["proposed_end_date"]
    if start is not None and end is not None:
        n = max_trip_days(merged["num_options"])
        if (_as_utc(end) - _as_utc(start)).days > n:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Trip duration exceeds the maximum of {n} days "
                    f"for {merged['num_options']} itinerary options"
                ),
            )
    for field, value in changes.items():
        setattr(trip, field, value)
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
    if trip.status == TripStatus.GENERATING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a trip while generation is in progress",
        )
    # FK ON DELETE CASCADE removes children; ai_call_logs.trip_id is SET NULL.
    await db.execute(delete(Trip).where(Trip.id == trip_id))
    await db.commit()


async def trigger_generation(
    trip_id: int,
    user_id: int,
    db: AsyncSession,
    background_tasks: BackgroundTasks,
    session_factory: async_sessionmaker[AsyncSession],
) -> dict:
    trip = await db.get(Trip, trip_id)
    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
        )
    if trip.creator_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )
    # Commit status change before returning so pollers see GENERATING immediately
    if not await start_generation(db, trip_id, _EDITABLE_STATUSES):
        await db.refresh(trip)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot generate from status '{trip.status}'",
        )
    background_tasks.add_task(generation.run_generation, trip_id, session_factory)
    return {"status": "accepted", "trip_id": trip_id}


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
