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
from app.schemas.trip import TripCreate, TripResponse, TripSummary
from app.services.email.sendgrid import EmailService
from app.services.generation import run_generation
from app.services.trips import create_trip, get_trip, list_trips_for_user

router = APIRouter(prefix="/trips", tags=["trips"])


@router.get("/", response_model=list[TripSummary])
async def list_trips(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[TripSummary]:
    return await list_trips_for_user(current_user.id, db)


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
    if trip.status not in ("CREATED", "COLLECTING_PREFERENCES"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot generate from status '{trip.status}'",
        )

    # Commit status change before returning so pollers see GENERATING immediately
    trip.status = "GENERATING"
    await db.commit()

    background_tasks.add_task(run_generation, trip_id, session_factory)
    return {"status": "accepted", "trip_id": trip_id}


@router.post("/{trip_id}/new-iteration")
async def trigger_new_iteration(trip_id: int) -> dict:
    # TODO: implement in iteration step
    raise NotImplementedError


@router.post("/{trip_id}/pick-winner")
async def pick_winner(trip_id: int, itinerary_id: int) -> dict:
    # TODO: implement in voting step
    raise NotImplementedError
