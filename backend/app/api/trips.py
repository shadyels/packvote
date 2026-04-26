from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.dependencies import (
    get_current_user,
    get_email_service,
    get_session_factory,
)
from app.db.session import get_db
from app.models.trip import Trip
from app.models.user import User
from app.schemas.itinerary import ItineraryResponse
from app.schemas.participant import ParticipantResponse
from app.schemas.trip import (
    InvitedTripSummary,
    TripCreate,
    TripResponse,
    TripSummary,
    TripUpdate,
)
from app.schemas.vote import PickWinnerRequest
from app.services.email.brevo import EmailService
from app.services.generation import run_generation
from app.services.trips import (
    create_trip,
    delete_trip,
    get_trip,
    list_invited_trips_for_user,
    list_itineraries_for_trip,
    list_participants_for_trip,
    list_trips_for_user,
    update_trip,
)
from app.services.voting.service import pick_winner, trigger_new_iteration

router = APIRouter(prefix="/trips", tags=["trips"])


@router.get("/", response_model=list[TripSummary])
async def list_trips(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[TripSummary]:
    return await list_trips_for_user(current_user.id, db)


@router.get("/invited", response_model=list[InvitedTripSummary])
async def list_invited(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[TripSummary]:
    return await list_invited_trips_for_user(current_user.id, db)


@router.post("/", response_model=TripResponse, status_code=201)
async def create_trip_handler(
    payload: TripCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    email_service: Annotated[EmailService, Depends(get_email_service)],
) -> TripResponse:
    return await create_trip(payload, current_user.id, db, email_service)


@router.get("/{trip_id}", response_model=TripResponse)
async def get_trip_handler(
    trip_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TripResponse:
    return await get_trip(trip_id, current_user.id, db)


@router.patch("/{trip_id}", response_model=TripResponse)
async def update_trip_handler(
    trip_id: int,
    payload: TripUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TripResponse:
    return await update_trip(trip_id, current_user.id, payload, db)


@router.delete("/{trip_id}", status_code=204)
async def delete_trip_handler(
    trip_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    await delete_trip(trip_id, current_user.id, db)


@router.post("/{trip_id}/generate", status_code=202)
async def trigger_generation(
    trip_id: int,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    session_factory: Annotated[async_sessionmaker, Depends(get_session_factory)],
) -> dict:
    result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = result.scalar_one_or_none()
    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found"
        )
    if trip.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )
    if trip.status not in ("CREATED", "COLLECTING_PREFERENCES", "GENERATION_FAILED"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot generate from status '{trip.status}'",
        )

    # Commit status change before returning so pollers see GENERATING immediately
    trip.generation_error = None
    trip.status = "GENERATING"
    await db.commit()

    background_tasks.add_task(run_generation, trip_id, session_factory)
    return {"status": "accepted", "trip_id": trip_id}


@router.post("/{trip_id}/new-iteration", status_code=202)
async def trigger_new_iteration_handler(
    trip_id: int,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    session_factory: Annotated[async_sessionmaker, Depends(get_session_factory)],
) -> dict:
    return await trigger_new_iteration(
        current_user, trip_id, db, background_tasks, session_factory
    )


@router.post("/{trip_id}/pick-winner")
async def pick_winner_handler(
    trip_id: int,
    payload: PickWinnerRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    trip = await pick_winner(current_user, trip_id, payload.itinerary_id, db)
    return {"status": "finalized", "winner_itinerary_id": trip.winner_itinerary_id}


@router.get("/{trip_id}/participants", response_model=list[ParticipantResponse])
async def get_trip_participants(
    trip_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict]:
    return await list_participants_for_trip(trip_id, current_user.id, db)


@router.get("/{trip_id}/itineraries", response_model=list[ItineraryResponse])
async def get_trip_itineraries(
    trip_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ItineraryResponse]:
    return await list_itineraries_for_trip(trip_id, current_user.id, db)
