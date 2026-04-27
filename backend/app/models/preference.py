from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Preference(Base):
    __tablename__ = "preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    participant_id: Mapped[int] = mapped_column(
        ForeignKey("participants.id"), nullable=False
    )
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id"), nullable=False)
    preferred_start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    preferred_end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    budget_min: Mapped[float | None] = mapped_column(Float)
    budget_max: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    interests: Mapped[str | None] = mapped_column(Text)  # free text
    activity_tags: Mapped[list[str] | None] = mapped_column(JSON)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    participant: Mapped[Participant] = relationship(
        "Participant", back_populates="preferences"
    )  # type: ignore[name-defined]
