from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas._limits import (
    ACTIVITY_TAG_MAX,
    ACTIVITY_TAGS_MAX_ITEMS,
    INTERESTS_MAX,
    NAME_MAX,
)
from app.schemas._sanitize import sanitize_text


class PreferenceCreate(BaseModel):
    name: str | None = Field(default=None, max_length=NAME_MAX)
    preferred_start_date: datetime | None = None
    preferred_end_date: datetime | None = None
    budget_min: float | None = Field(default=None, ge=0)
    budget_max: float | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    interests: str | None = Field(default=None, max_length=INTERESTS_MAX)
    activity_tags: list[str] | None = None

    @field_validator("name", mode="after")
    @classmethod
    def sanitize_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return sanitize_text(v)

    @field_validator("interests", mode="after")
    @classmethod
    def sanitize_interests(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = sanitize_text(v)
        return v if v else None

    @field_validator("activity_tags", mode="after")
    @classmethod
    def sanitize_activity_tags(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        if len(v) > ACTIVITY_TAGS_MAX_ITEMS:
            raise ValueError(f"activity_tags may contain at most {ACTIVITY_TAGS_MAX_ITEMS} items")
        result = []
        for tag in v:
            if len(tag) > ACTIVITY_TAG_MAX:
                raise ValueError(f"each activity tag may be at most {ACTIVITY_TAG_MAX} characters")
            sanitized = sanitize_text(tag)
            if sanitized:
                result.append(sanitized)
        return result if result else None


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
