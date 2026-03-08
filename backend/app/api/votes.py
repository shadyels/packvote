from fastapi import APIRouter

from app.schemas.vote import VoteResponse, VoteSubmit, VotingResults

router = APIRouter(prefix="/votes", tags=["votes"])


@router.post("/trips/{trip_id}/vote", response_model=VoteResponse, status_code=201)
async def submit_vote(trip_id: int, payload: VoteSubmit) -> VoteResponse:
    # TODO: implement in voting step
    raise NotImplementedError


@router.get("/trips/{trip_id}/results", response_model=VotingResults)
async def get_voting_results(trip_id: int) -> VotingResults:
    # TODO: implement in voting step
    raise NotImplementedError
