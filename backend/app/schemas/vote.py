from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas._limits import RANKINGS_MAX


class VoteSubmit(BaseModel):
    rankings: list[int] = Field(max_length=RANKINGS_MAX)  # ordered list of itinerary IDs, most preferred first

    @field_validator("rankings", mode="after")
    @classmethod
    def check_unique_rankings(cls, v: list[int]) -> list[int]:
        if len(v) != len(set(v)):
            raise ValueError("rankings must contain unique itinerary IDs")
        return v


class VoteResponse(BaseModel):
    id: int
    participant_id: int | None
    trip_id: int
    iteration_number: int
    rankings: list[int]
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
