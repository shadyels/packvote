from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends

from app.core.dependencies import DB, CurrentUser, get_results_trip
from app.models.trip import Trip
from app.schemas.vote import VoteResponse, VoteSubmit, VotingResults
from app.services.voting.service import (
    compute_results,
    submit_admin_vote,
    submit_participant_vote,
)

router = APIRouter(prefix="/votes", tags=["votes"])


@router.post(
    "/trips/{trip_id}/vote/{token}", response_model=VoteResponse, status_code=201
)
async def submit_vote(
    trip_id: int,
    token: str,
    payload: VoteSubmit,
    db: DB,
    background_tasks: BackgroundTasks,
) -> VoteResponse:
    return await submit_participant_vote(
        token, trip_id, payload.rankings, db, background_tasks
    )


@router.post(
    "/trips/{trip_id}/admin-vote", response_model=VoteResponse, status_code=201
)
async def submit_admin_vote_handler(
    trip_id: int,
    payload: VoteSubmit,
    current_user: CurrentUser,
    db: DB,
    background_tasks: BackgroundTasks,
) -> VoteResponse:
    return await submit_admin_vote(
        current_user, trip_id, payload.rankings, db, background_tasks
    )


@router.get("/trips/{trip_id}/results", response_model=VotingResults)
async def get_voting_results(
    trip: Annotated[Trip, Depends(get_results_trip)],
    db: DB,
    iteration: int | None = None,
) -> VotingResults:
    return await compute_results(db, trip, iteration)
