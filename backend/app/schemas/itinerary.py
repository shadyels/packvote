from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, field_validator

TIME_SLOTS = ("morning", "afternoon", "evening", "night")


class DailyActivity(BaseModel):
    # Part of day. Lenient on purpose: an AI typo must not fail a rate-limited
    # generation, and rows stored before v4 hold clock times or null.
    time: Literal["morning", "afternoon", "evening", "night"] | None = None
    title: str
    description: str
    estimated_cost: float | None = None  # Phase 2 price field

    @field_validator("time", mode="before")
    @classmethod
    def _coerce_time_slot(cls, v: Any) -> str | None:
        slot = v.strip().lower() if isinstance(v, str) else None
        return slot if slot in TIME_SLOTS else None


class DayItinerary(BaseModel):
    day_number: int
    title: str
    activities: list[DailyActivity]
    estimated_cost: float | None = None  # Phase 2 price field


class ItineraryOption(BaseModel):
    """AI-generated itinerary option — validated output schema."""

    option_title: str
    destination_name: str
    destination_description: str
    daily_itinerary: list[DayItinerary]
    total_estimated_budget: float
    currency: str
    match_reasoning: str
    highlights: list[str]


class AIGenerationResponse(BaseModel):
    """Top-level AI response wrapping N itinerary options."""

    options: list[ItineraryOption]


class ItineraryResponse(BaseModel):
    id: int
    trip_id: int
    iteration_number: int
    option_title: str | None
    destination_name: str
    destination_description: str
    daily_itinerary: list[DayItinerary]
    total_estimated_budget: float
    currency: str
    match_reasoning: str
    highlights: list[str]
    model_used: str | None
    provider: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
