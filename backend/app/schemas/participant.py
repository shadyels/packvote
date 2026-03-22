from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.itinerary import ItineraryResponse
from app.schemas.vote import VotingResults


class ParticipantResponse(BaseModel):
    id: int
    trip_id: int
    email: str
    name: str | None
    preferences_submitted: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TripAccessByCode(BaseModel):
    trip_code: str
    pin: str


class TripPublicInfo(BaseModel):
    """Trip details visible to participants (no creator-only fields)."""

    id: int
    title: str
    destination: str | None
    proposed_start_date: date | None
    proposed_end_date: date | None
    status: str
    num_options: int
    current_iteration: int
    winner_itinerary_id: int | None
    generation_error: str | None = None

    model_config = {"from_attributes": True}


class ParticipantBrief(BaseModel):
    """Participant info visible to other participants — names/initials only, no emails."""

    id: int
    name: str | None
    preferences_submitted: bool

    model_config = {"from_attributes": True}


class ParticipantTripView(BaseModel):
    """Everything a participant needs to see on the trip page."""

    participant: ParticipantResponse
    trip: TripPublicInfo
    participants: list[ParticipantBrief]
    itineraries: list[ItineraryResponse]
    voting_results: VotingResults | None
    has_voted: bool


class ParticipantAccessResponse(BaseModel):
    token: str
    participant: ParticipantResponse
