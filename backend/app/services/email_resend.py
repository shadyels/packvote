from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.itinerary import Itinerary
from app.models.participant import Participant
from app.models.trip import Trip, TripStatus
from app.services.email.brevo import EmailKind, EmailService

_KIND_BY_STATUS: dict[TripStatus, EmailKind] = {
    TripStatus.CREATED: "invitation",
    TripStatus.COLLECTING_PREFERENCES: "invitation",
    TripStatus.GENERATING: "invitation",
    TripStatus.GENERATION_FAILED: "invitation",
    TripStatus.VOTING: "voting",
    TripStatus.FINALIZED: "finalized",
}


async def resend_emails_for_trip(
    trip: Trip,
    participants: list[Participant],
    db: AsyncSession,
    email_service: EmailService,
) -> tuple[int, int]:
    """Send status-appropriate email to each participant.

    Returns (sent_count, failed_count).
    Raises ValueError if FINALIZED but winner itinerary is missing.
    """
    destination_name: str | None = None
    if trip.status == TripStatus.FINALIZED:
        if trip.winner_itinerary_id is None:
            raise ValueError("Trip is finalized but has no winner itinerary set.")
        result = await db.execute(
            select(Itinerary).where(Itinerary.id == trip.winner_itinerary_id)
        )
        itinerary = result.scalar_one_or_none()
        if itinerary is None:
            raise ValueError("Winner itinerary record not found.")
        destination_name = itinerary.destination_name

    if trip.status == TripStatus.VOTING and trip.current_iteration > 1:
        kind: EmailKind | None = "new_iteration"
    else:
        kind = _KIND_BY_STATUS.get(trip.status)
    if kind is None:
        return 0, len(participants)
    results = await asyncio.gather(
        *[
            email_service.send_trip_email(
                kind,
                to_email=p.email,
                participant_name=p.name,
                trip_title=trip.title,
                trip_code=trip.trip_code,
                pin=p.pin,
                token=p.token,
                destination_name=destination_name or "",
            )
            for p in participants
        ],
        return_exceptions=True,
    )
    sent = sum(1 for r in results if r is True)
    return sent, len(results) - sent


async def list_trip_participants(trip_id: int, db: AsyncSession) -> list[Participant]:
    result = await db.execute(select(Participant).where(Participant.trip_id == trip_id))
    return list(result.scalars().all())


async def get_trip_participant(
    trip_id: int, participant_id: int, db: AsyncSession
) -> Participant | None:
    result = await db.execute(
        select(Participant).where(
            Participant.id == participant_id, Participant.trip_id == trip_id
        )
    )
    return result.scalar_one_or_none()
