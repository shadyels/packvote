from datetime import datetime

from pydantic import BaseModel


class VoteSubmit(BaseModel):
    rankings: list[int]  # ordered list of itinerary IDs, most preferred first


class VoteResponse(BaseModel):
    id: int
    participant_id: int | None
    trip_id: int
    iteration_number: int
    rankings_json: str
    submitted_at: datetime

    model_config = {"from_attributes": True}


class PickWinnerRequest(BaseModel):
    itinerary_id: int


class VoteRoundResult(BaseModel):
    round_number: int
    results: dict[int, int]  # itinerary_id -> vote count
    eliminated_option_id: int | None
    winner_id: int | None


class VotingResults(BaseModel):
    trip_id: int
    iteration_number: int
    rounds: list[VoteRoundResult]
    winner_id: int | None
    is_complete: bool
