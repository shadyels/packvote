from datetime import datetime

from pydantic import BaseModel, Field


class PreferenceCreate(BaseModel):
    preferred_start_date: datetime | None = None
    preferred_end_date: datetime | None = None
    budget_min: float | None = Field(default=None, ge=0)
    budget_max: float | None = Field(default=None, ge=0)
    currency: str = "USD"
    interests: str | None = None
    activity_tags: list[str] | None = None


class PreferenceResponse(BaseModel):
    id: int
    participant_id: int
    trip_id: int
    preferred_start_date: datetime | None
    preferred_end_date: datetime | None
    budget_min: float | None
    budget_max: float | None
    currency: str
    interests: str | None
    submitted_at: datetime

    model_config = {"from_attributes": True}
