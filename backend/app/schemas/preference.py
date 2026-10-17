from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

from app.schemas._limits import (
    ACTIVITY_TAG_MAX,
    ACTIVITY_TAGS_MAX_ITEMS,
    INTERESTS_MAX,
    NAME_MAX,
)
from app.schemas._sanitize import CleanStr


def _blank_to_none(v: str | None) -> str | None:
    return v or None


def _clean_tags(v: list[str] | None) -> list[str] | None:
    return [t for t in v if t] or None if v else None


class PreferenceCreate(BaseModel):
    name: Annotated[CleanStr | None, Field(max_length=NAME_MAX)] = None
    preferred_start_date: datetime | None = None
    preferred_end_date: datetime | None = None
    budget_min: float | None = Field(default=None, ge=0)
    budget_max: float | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    interests: Annotated[
        CleanStr | None,
        Field(max_length=INTERESTS_MAX),
        AfterValidator(_blank_to_none),
    ] = None
    # Per-tag length is checked before sanitising (as before); blanks are dropped.
    activity_tags: Annotated[
        list[Annotated[CleanStr, Field(max_length=ACTIVITY_TAG_MAX)]] | None,
        Field(max_length=ACTIVITY_TAGS_MAX_ITEMS),
        AfterValidator(_clean_tags),
    ] = None


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
