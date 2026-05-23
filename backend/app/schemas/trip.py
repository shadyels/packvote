from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.schemas._limits import (
    DESTINATION_MAX,
    NOTES_MAX,
    PARTICIPANT_EMAILS_MAX,
    TITLE_MAX,
    max_trip_days,
)
from app.schemas._sanitize import sanitize_text


class TripCreate(BaseModel):
    title: str = Field(min_length=1, max_length=TITLE_MAX)
    destination: str | None = Field(default=None, max_length=DESTINATION_MAX)
    proposed_start_date: datetime | None = None
    proposed_end_date: datetime | None = None
    num_options: int = Field(default=3, ge=2, le=5)
    participant_emails: list[EmailStr] = Field(
        min_length=1, max_length=PARTICIPANT_EMAILS_MAX
    )
    notes: str | None = Field(default=None, max_length=NOTES_MAX)

    @field_validator("title", mode="after")
    @classmethod
    def sanitize_title(cls, v: str) -> str:
        v = sanitize_text(v)
        if not v:
            raise ValueError("title must not be empty")
        return v

    @field_validator("destination", mode="after")
    @classmethod
    def sanitize_destination(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return sanitize_text(v)

    @field_validator("notes", mode="after")
    @classmethod
    def sanitize_notes(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return sanitize_text(v)

    @model_validator(mode="after")
    def check_date_range(self) -> "TripCreate":
        if self.proposed_start_date is not None and self.proposed_end_date is not None:
            n = max_trip_days(self.num_options)
            duration = (self.proposed_end_date - self.proposed_start_date).days
            if duration > n:
                raise ValueError(
                    f"Trip duration exceeds the maximum of {n} days for {self.num_options} itinerary options"
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
    title: Annotated[str | None, Field(default=None, max_length=TITLE_MAX)]
    destination: Annotated[str | None, Field(default=None, max_length=DESTINATION_MAX)]
    proposed_start_date: datetime | None = None
    proposed_end_date: datetime | None = None
    num_options: Annotated[int | None, Field(default=None, ge=2, le=5)]
    notes: Annotated[str | None, Field(default=None, max_length=NOTES_MAX)]

    @field_validator("title", mode="after")
    @classmethod
    def sanitize_title(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = sanitize_text(v)
        if not v:
            raise ValueError("title must not be empty")
        return v

    @field_validator("destination", mode="after")
    @classmethod
    def sanitize_destination(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return sanitize_text(v)

    @field_validator("notes", mode="after")
    @classmethod
    def sanitize_notes(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return sanitize_text(v)

    @model_validator(mode="after")
    def check_date_range(self) -> "TripUpdate":
        if (
            self.proposed_start_date is not None
            and self.proposed_end_date is not None
            and self.num_options is not None
        ):
            n = max_trip_days(self.num_options)
            duration = (self.proposed_end_date - self.proposed_start_date).days
            if duration > n:
                raise ValueError(
                    f"Trip duration exceeds the maximum of {n} days for {self.num_options} itinerary options"
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
