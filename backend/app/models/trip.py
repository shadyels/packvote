from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(primary_key=True)
    trip_code: Mapped[str] = mapped_column(String(8), unique=True, nullable=False, index=True)
    pin: Mapped[str] = mapped_column(String(4), nullable=False)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    destination: Mapped[str | None] = mapped_column(String(255))  # None = "surprise me"
    proposed_start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    proposed_end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    num_options: Mapped[int] = mapped_column(Integer, default=3)  # 2–5
    status: Mapped[str] = mapped_column(
        String(50), default="CREATED"
    )  # CREATED | COLLECTING_PREFERENCES | GENERATING | VOTING | ITERATING | FINALIZED
    max_iterations: Mapped[int] = mapped_column(Integer, default=10)
    current_iteration: Mapped[int] = mapped_column(Integer, default=0)
    winner_itinerary_id: Mapped[int | None] = mapped_column(ForeignKey("itineraries.id"))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    creator: Mapped[User] = relationship("User", back_populates="trips")  # type: ignore[name-defined]
    participants: Mapped[list[Participant]] = relationship("Participant", back_populates="trip")  # type: ignore[name-defined]
    itineraries: Mapped[list[Itinerary]] = relationship("Itinerary", back_populates="trip", foreign_keys="Itinerary.trip_id")  # type: ignore[name-defined]
    votes: Mapped[list[Vote]] = relationship("Vote", back_populates="trip")  # type: ignore[name-defined]
    vote_rounds: Mapped[list[VoteRound]] = relationship("VoteRound", back_populates="trip")  # type: ignore[name-defined]
