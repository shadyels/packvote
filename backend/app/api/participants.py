from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.dependencies import get_session_factory
from app.db.session import get_db
from app.schemas.participant import (
    ParticipantAccessResponse,
    ParticipantResponse,
    ParticipantTripView,
    TripAccessByCode,
)
from app.schemas.preference import PreferenceCreate, PreferenceResponse
from app.services.participants import (
    access_trip_by_code,
    get_participant_by_token,
    get_participant_trip_view,
)
from app.services.participants import (
    submit_preferences as svc_submit_preferences,
)

router = APIRouter(prefix="/participants", tags=["participants"])


@router.post("/access-by-code", response_model=ParticipantAccessResponse)
async def access_by_code(
    payload: TripAccessByCode,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ParticipantAccessResponse:
    participant = await access_trip_by_code(payload.trip_code, payload.pin, db)
    return ParticipantAccessResponse(
        token=participant.token,
        participant=ParticipantResponse.model_validate(participant),
    )


@router.get("/{token}/trip-view", response_model=ParticipantTripView)
async def get_trip_view(
    token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ParticipantTripView:
    return await get_participant_trip_view(token, db)


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
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    session_factory: Annotated[async_sessionmaker, Depends(get_session_factory)],
) -> PreferenceResponse:
    return await svc_submit_preferences(
        token, payload, db, background_tasks, session_factory
    )
