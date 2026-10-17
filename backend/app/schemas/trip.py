from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.schemas._limits import (
    DESTINATION_MAX,
    NOTES_MAX,
    PARTICIPANT_EMAILS_MAX,
    TITLE_MAX,
    check_trip_duration,
)
from app.schemas._sanitize import CleanStr, NonEmptyCleanStr


class TripCreate(BaseModel):
    title: Annotated[NonEmptyCleanStr, Field(min_length=1, max_length=TITLE_MAX)]
    destination: Annotated[CleanStr | None, Field(max_length=DESTINATION_MAX)] = None
    proposed_start_date: datetime | None = None
    proposed_end_date: datetime | None = None
    num_options: int = Field(default=3, ge=2, le=5)
    participant_emails: list[EmailStr] = Field(
        min_length=1, max_length=PARTICIPANT_EMAILS_MAX
    )
    notes: Annotated[CleanStr | None, Field(max_length=NOTES_MAX)] = None

    @model_validator(mode="after")
    def check_date_range(self) -> "TripCreate":
        check_trip_duration(
            self.proposed_start_date, self.proposed_end_date, self.num_options
        )
        return self


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
    title: Annotated[NonEmptyCleanStr | None, Field(max_length=TITLE_MAX)] = None
    destination: Annotated[CleanStr | None, Field(max_length=DESTINATION_MAX)] = None
    proposed_start_date: datetime | None = None
    proposed_end_date: datetime | None = None
    num_options: Annotated[int | None, Field(ge=2, le=5)] = None
    notes: Annotated[CleanStr | None, Field(max_length=NOTES_MAX)] = None

    @model_validator(mode="after")
    def check_date_range(self) -> "TripUpdate":
        check_trip_duration(
            self.proposed_start_date, self.proposed_end_date, self.num_options
        )
        return self


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


class InvitedTripSummary(TripSummary):
    participant_token: str


class GenerationAccepted(BaseModel):
    status: str
    trip_id: int
