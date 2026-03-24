from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field


class TripCreate(BaseModel):
    title: str
    destination: str | None = None  # None = "surprise me"
    proposed_start_date: datetime | None = None
    proposed_end_date: datetime | None = None
    num_options: int = Field(default=3, ge=2, le=5)
    participant_emails: list[str]
    notes: str | None = None


class TripResponse(BaseModel):
    id: int
    trip_code: str
    creator_id: int
    title: str
    destination: str | None
    proposed_start_date: datetime | None
    proposed_end_date: datetime | None
    num_options: int
    status: str
    current_iteration: int
    max_iterations: int
    winner_itinerary_id: int | None
    generation_error: str | None = None
    notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TripUpdate(BaseModel):
    title: str | None = None
    destination: Annotated[str | None, Field(default=None)]
    proposed_start_date: datetime | None = None
    proposed_end_date: datetime | None = None
    num_options: Annotated[int | None, Field(default=None, ge=2, le=5)]
    notes: str | None = None


class TripSummary(BaseModel):
    id: int
    trip_code: str
    title: str
    destination: str | None
    status: str
    participant_count: int
    preferences_submitted_count: int
    created_at: datetime

    model_config = {"from_attributes": True}
