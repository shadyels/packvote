from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_email_service
from app.db.session import get_db
from app.models.participant import Participant
from app.models.trip import Trip
from app.models.user import User
from app.services.email.brevo import EmailService
from app.services.email_resend import resend_emails_for_trip

router = APIRouter(prefix="/admin", tags=["admin"])


class ResendEmailResponse(BaseModel):
    sent: int
    failed: int


async def _require_trip_creator(
    trip_id: int,
    current_user: User,
    db: AsyncSession,
) -> Trip:
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()
    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
        )
    if trip.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not the trip creator"
        )
    return trip


@router.post("/trips/{trip_id}/resend-emails", response_model=ResendEmailResponse)
async def resend_all_emails(
    trip_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    email_service: Annotated[EmailService, Depends(get_email_service)],
) -> ResendEmailResponse:
    trip = await _require_trip_creator(trip_id, current_user, db)
    result = await db.execute(select(Participant).where(Participant.trip_id == trip_id))
    participants = list(result.scalars().all())
    try:
        sent, failed = await resend_emails_for_trip(
            trip, participants, db, email_service
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    return ResendEmailResponse(sent=sent, failed=failed)


@router.post(
    "/trips/{trip_id}/participants/{participant_id}/resend-email",
    response_model=ResendEmailResponse,
)
async def resend_one_email(
    trip_id: int,
    participant_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    email_service: Annotated[EmailService, Depends(get_email_service)],
) -> ResendEmailResponse:
    trip = await _require_trip_creator(trip_id, current_user, db)
    result = await db.execute(
        select(Participant).where(
            Participant.id == participant_id,
            Participant.trip_id == trip_id,
        )
    )
    participant = result.scalar_one_or_none()
    if participant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found"
        )
    try:
        sent, failed = await resend_emails_for_trip(
            trip, [participant], db, email_service
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    return ResendEmailResponse(sent=sent, failed=failed)
