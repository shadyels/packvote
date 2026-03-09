from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.participant import ParticipantResponse, TripAccessByCode
from app.schemas.preference import PreferenceCreate, PreferenceResponse
from app.services.participants import (
    access_trip_by_code,
    get_participant_by_token,
    submit_preferences as svc_submit_preferences,
)

router = APIRouter(prefix="/participants", tags=["participants"])


@router.post("/access-by-code", response_model=ParticipantResponse)
async def access_by_code(
    payload: TripAccessByCode,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ParticipantResponse:
    return await access_trip_by_code(payload.trip_code, payload.pin, db)


@router.get("/{token}", response_model=ParticipantResponse)
async def get_participant_by_token_handler(
    token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ParticipantResponse:
    return await get_participant_by_token(token, db)


@router.post("/{token}/preferences", response_model=PreferenceResponse, status_code=201)
async def submit_preferences(
    token: str,
    payload: PreferenceCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PreferenceResponse:
    return await svc_submit_preferences(token, payload, db)
