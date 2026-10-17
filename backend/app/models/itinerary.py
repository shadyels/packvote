from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONType


class Itinerary(Base):
    __tablename__ = "itineraries"

    id: Mapped[int] = mapped_column(primary_key=True)
    trip_id: Mapped[int] = mapped_column(
        ForeignKey("trips.id", ondelete="CASCADE"), index=True
    )
    iteration_number: Mapped[int] = mapped_column(Integer, default=1)
    option_title: Mapped[str | None] = mapped_column(String(255))
    destination_name: Mapped[str] = mapped_column(String(255))
    destination_description: Mapped[str] = mapped_column(Text)
    daily_itinerary: Mapped[list] = mapped_column(JSONType)
    total_estimated_budget: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    match_reasoning: Mapped[str] = mapped_column(Text)
    highlights: Mapped[list[str]] = mapped_column(JSONType)

    # AI generation metadata
    prompt_version: Mapped[str | None] = mapped_column(String(20))
    model_used: Mapped[str | None] = mapped_column(String(255))
    provider: Mapped[str | None] = mapped_column(String(100))
    generation_latency_ms: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
