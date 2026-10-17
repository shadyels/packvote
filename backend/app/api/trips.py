from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.dependencies import (
    DB,
    CurrentUser,
    get_email_service,
    get_session_factory,
)
from app.schemas.itinerary import ItineraryResponse
from app.schemas.participant import ParticipantResponse
from app.schemas.trip import (
    GenerationAccepted,
    InvitedTripSummary,
    TripCreate,
    TripResponse,
    TripSummary,
    TripUpdate,
)
from app.schemas.vote import PickWinnerRequest, PickWinnerResponse
from app.services.email.brevo import EmailService
from app.services.trips import (
    create_trip,
    delete_trip,
    get_owned_trip,
    list_invited_trips_for_user,
    list_itineraries_for_trip,
    list_participants_for_trip,
    list_trips_for_user,
    trigger_generation,
    update_trip,
)
from app.services.voting.service import pick_winner, trigger_new_iteration

router = APIRouter(prefix="/trips", tags=["trips"])


@router.get("/", response_model=list[TripSummary])
async def list_trips(
    current_user: CurrentUser,
    db: DB,
) -> list[TripSummary]:
    return await list_trips_for_user(current_user.id, db)


@router.get("/invited", response_model=list[InvitedTripSummary])
async def list_invited(
    current_user: CurrentUser,
    db: DB,
) -> list[InvitedTripSummary]:
    return await list_invited_trips_for_user(current_user.id, db)


@router.post("/", response_model=TripResponse, status_code=201)
async def create_trip_handler(
    payload: TripCreate,
    current_user: CurrentUser,
    db: DB,
    email_service: Annotated[EmailService, Depends(get_email_service)],
    background_tasks: BackgroundTasks,
) -> TripResponse:
    return await create_trip(
        payload, current_user.id, db, email_service, background_tasks
    )


@router.get("/{trip_id}", response_model=TripResponse)
async def get_trip_handler(
    trip_id: int,
    current_user: CurrentUser,
    db: DB,
) -> TripResponse:
    return await get_owned_trip(db, trip_id, current_user)


@router.patch("/{trip_id}", response_model=TripResponse)
async def update_trip_handler(
    trip_id: int,
    payload: TripUpdate,
    current_user: CurrentUser,
    db: DB,
) -> TripResponse:
    return await update_trip(trip_id, current_user, payload, db)


@router.delete("/{trip_id}", status_code=204)
async def delete_trip_handler(
    trip_id: int,
    current_user: CurrentUser,
    db: DB,
) -> None:
    await delete_trip(trip_id, current_user, db)


@router.post("/{trip_id}/generate", response_model=GenerationAccepted, status_code=202)
async def trigger_generation_handler(
    trip_id: int,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: DB,
    session_factory: Annotated[async_sessionmaker, Depends(get_session_factory)],
) -> dict:
    return await trigger_generation(
        trip_id, current_user, db, background_tasks, session_factory
    )


@router.post(
    "/{trip_id}/new-iteration", response_model=GenerationAccepted, status_code=202
)
async def trigger_new_iteration_handler(
    trip_id: int,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: DB,
    session_factory: Annotated[async_sessionmaker, Depends(get_session_factory)],
) -> dict:
    return await trigger_new_iteration(
        current_user, trip_id, db, background_tasks, session_factory
    )


@router.post("/{trip_id}/pick-winner", response_model=PickWinnerResponse)
async def pick_winner_handler(
    trip_id: int,
    payload: PickWinnerRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: DB,
) -> PickWinnerResponse:
    trip = await pick_winner(
        current_user, trip_id, payload.itinerary_id, db, background_tasks
    )
    return PickWinnerResponse(
        status="finalized", winner_itinerary_id=trip.winner_itinerary_id
    )


@router.get("/{trip_id}/participants", response_model=list[ParticipantResponse])
async def get_trip_participants(
    trip_id: int,
    current_user: CurrentUser,
    db: DB,
) -> list[dict]:
    return await list_participants_for_trip(trip_id, current_user, db)


@router.get("/{trip_id}/itineraries", response_model=list[ItineraryResponse])
async def get_trip_itineraries(
    trip_id: int,
    current_user: CurrentUser,
    db: DB,
) -> list[ItineraryResponse]:
    return await list_itineraries_for_trip(trip_id, current_user, db)
