from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Vote(Base):
    __tablename__ = "votes"

    id: Mapped[int] = mapped_column(primary_key=True)
    participant_id: Mapped[int] = mapped_column(
        ForeignKey("participants.id"), nullable=False
    )
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id"), nullable=False)
    iteration_number: Mapped[int] = mapped_column(Integer, default=1)
    rankings_json: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # JSON: [itinerary_id, ...]
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    participant: Mapped[Participant] = relationship(
        "Participant", back_populates="votes"
    )  # type: ignore[name-defined]
    trip: Mapped[Trip] = relationship("Trip", back_populates="votes")  # type: ignore[name-defined]
