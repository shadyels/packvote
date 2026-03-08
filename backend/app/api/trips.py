from fastapi import APIRouter

from app.schemas.trip import TripCreate, TripResponse, TripSummary

router = APIRouter(prefix="/trips", tags=["trips"])


@router.get("/", response_model=list[TripSummary])
async def list_trips() -> list[TripSummary]:
    # TODO: implement in trip CRUD step
    raise NotImplementedError


@router.post("/", response_model=TripResponse, status_code=201)
async def create_trip(payload: TripCreate) -> TripResponse:
    # TODO: implement in trip CRUD step
    raise NotImplementedError


@router.get("/{trip_id}", response_model=TripResponse)
async def get_trip(trip_id: int) -> TripResponse:
    # TODO: implement in trip CRUD step
    raise NotImplementedError


@router.post("/{trip_id}/generate")
async def trigger_generation(trip_id: int) -> dict:
    # TODO: implement in AI pipeline step
    raise NotImplementedError


@router.post("/{trip_id}/new-iteration")
async def trigger_new_iteration(trip_id: int) -> dict:
    # TODO: implement in iteration step
    raise NotImplementedError


@router.post("/{trip_id}/pick-winner")
async def pick_winner(trip_id: int, itinerary_id: int) -> dict:
    # TODO: implement in voting step
    raise NotImplementedError
