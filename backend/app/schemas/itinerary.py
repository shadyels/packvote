from datetime import datetime

from pydantic import BaseModel


class DailyActivity(BaseModel):
    time: str | None = None
    title: str
    description: str
    estimated_cost: float | None = None  # Phase 2 price field


class DayItinerary(BaseModel):
    day_number: int
    title: str
    activities: list[DailyActivity]
    estimated_cost: float | None = None  # Phase 2 price field


class ItineraryOption(BaseModel):
    """AI-generated itinerary option — validated output schema."""

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
    destination_name: str
    destination_description: str
    daily_itinerary_json: str
    total_estimated_budget: float
    currency: str
    match_reasoning: str
    highlights: str
    model_used: str | None
    provider: str | None
    created_at: datetime

    # Phase 2 price fields
    estimated_cost: float | None
    price_last_updated: datetime | None
    price_source: str | None

    model_config = {"from_attributes": True}
