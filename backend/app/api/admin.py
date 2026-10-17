from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.dependencies import DB, CurrentUser, get_email_service
from app.services.email.brevo import EmailService
from app.services.email_resend import (
    get_trip_participant,
    list_trip_participants,
    resend_emails_for_trip,
)
from app.services.trips import get_owned_trip

router = APIRouter(prefix="/admin", tags=["admin"])


class ResendEmailResponse(BaseModel):
    sent: int
    failed: int


@router.post("/trips/{trip_id}/resend-emails", response_model=ResendEmailResponse)
async def resend_all_emails(
    trip_id: int,
    current_user: CurrentUser,
    db: DB,
    email_service: Annotated[EmailService, Depends(get_email_service)],
) -> ResendEmailResponse:
    trip = await get_owned_trip(db, trip_id, current_user)
    participants = await list_trip_participants(trip_id, db)
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
    current_user: CurrentUser,
    db: DB,
    email_service: Annotated[EmailService, Depends(get_email_service)],
) -> ResendEmailResponse:
    trip = await get_owned_trip(db, trip_id, current_user)
    participant = await get_trip_participant(trip_id, participant_id, db)
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
