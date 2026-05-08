from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.itinerary import Itinerary
from app.models.participant import Participant
from app.models.trip import Trip
from app.services.email.brevo import EmailService


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
    if trip.status == "FINALIZED":
        if trip.winner_itinerary_id is None:
            raise ValueError("Trip is finalized but has no winner itinerary set.")
        result = await db.execute(
            select(Itinerary).where(Itinerary.id == trip.winner_itinerary_id)
        )
        itinerary = result.scalar_one_or_none()
        if itinerary is None:
            raise ValueError("Winner itinerary record not found.")
        destination_name = itinerary.destination_name

    sent = failed = 0
    for p in participants:
        ok = await _send_for_status(trip, p, email_service, destination_name)
        if ok:
            sent += 1
        else:
            failed += 1
    return sent, failed


async def _send_for_status(
    trip: Trip,
    participant: Participant,
    email_service: EmailService,
    destination_name: str | None,
) -> bool:
    kwargs: dict = dict(
        to_email=participant.email,
        participant_name=participant.name,
        trip_title=trip.title,
        trip_code=trip.trip_code,
        pin=participant.pin,
        token=participant.token,
    )
    if trip.status in (
        "CREATED",
        "COLLECTING_PREFERENCES",
        "GENERATING",
        "GENERATION_FAILED",
    ):
        return await email_service.send_invitation(**kwargs)
    if trip.status == "VOTING":
        if trip.current_iteration <= 1:
            return await email_service.send_voting_notification(**kwargs)
        return await email_service.send_new_iteration_notification(**kwargs)
    if trip.status == "ITERATING":
        return await email_service.send_new_iteration_notification(**kwargs)
    if trip.status == "FINALIZED":
        return await email_service.send_finalized_notification(
            **kwargs, destination_name=destination_name or ""
        )
    return False
