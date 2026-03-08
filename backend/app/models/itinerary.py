from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Itinerary(Base):
    __tablename__ = "itineraries"

    id: Mapped[int] = mapped_column(primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id"), nullable=False)
    iteration_number: Mapped[int] = mapped_column(Integer, default=1)
    destination_name: Mapped[str] = mapped_column(String(255), nullable=False)
    destination_description: Mapped[str] = mapped_column(Text, nullable=False)
    daily_itinerary_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON
    total_estimated_budget: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    match_reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    highlights: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array

    # AI generation metadata
    prompt_version_id: Mapped[int | None] = mapped_column(ForeignKey("prompt_templates.id"))
    model_used: Mapped[str | None] = mapped_column(String(255))
    provider: Mapped[str | None] = mapped_column(String(100))
    generation_latency_ms: Mapped[int | None] = mapped_column(Integer)

    # Phase 2: price monitoring fields (nullable — not populated in Phase 1)
    estimated_cost: Mapped[float | None] = mapped_column(Float)
    price_last_updated: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    price_source: Mapped[str | None] = mapped_column(String(255))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    trip: Mapped[Trip] = relationship("Trip", back_populates="itineraries", foreign_keys=[trip_id])  # type: ignore[name-defined]
    prompt_template: Mapped[PromptTemplate | None] = relationship("PromptTemplate")  # type: ignore[name-defined]
