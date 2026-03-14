from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.vote import VoteResponse, VoteSubmit, VotingResults
from app.services.voting.service import (
    get_or_compute_results,
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
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VoteResponse:
    return await submit_participant_vote(token, trip_id, payload.rankings, db)


@router.post(
    "/trips/{trip_id}/admin-vote", response_model=VoteResponse, status_code=201
)
async def submit_admin_vote_handler(
    trip_id: int,
    payload: VoteSubmit,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VoteResponse:
    return await submit_admin_vote(current_user, trip_id, payload.rankings, db)


@router.get("/trips/{trip_id}/results", response_model=VotingResults)
async def get_voting_results(
    trip_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    iteration: int | None = None,
) -> VotingResults:
    return await get_or_compute_results(trip_id, iteration, db)
