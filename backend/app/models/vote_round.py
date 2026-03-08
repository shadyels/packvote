from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class VoteRound(Base):
    __tablename__ = "vote_rounds"

    id: Mapped[int] = mapped_column(primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id"), nullable=False)
    iteration_number: Mapped[int] = mapped_column(Integer, default=1)
    round_number: Mapped[int] = mapped_column(Integer, default=1)
    eliminated_option_id: Mapped[int | None] = mapped_column(ForeignKey("itineraries.id"))
    results_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON: {itinerary_id: vote_count}
    winner_id: Mapped[int | None] = mapped_column(ForeignKey("itineraries.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    trip: Mapped[Trip] = relationship("Trip", back_populates="vote_rounds")  # type: ignore[name-defined]
