from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TripStatus(StrEnum):
    CREATED = "CREATED"
    COLLECTING_PREFERENCES = "COLLECTING_PREFERENCES"
    GENERATING = "GENERATING"
    GENERATION_FAILED = "GENERATION_FAILED"
    VOTING = "VOTING"
    FINALIZED = "FINALIZED"


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(primary_key=True)
    trip_code: Mapped[str] = mapped_column(String(8), unique=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    destination: Mapped[str | None] = mapped_column(String(255))  # None = "surprise me"
    proposed_start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    proposed_end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    num_options: Mapped[int] = mapped_column(Integer, default=3)  # 2–5
    status: Mapped[str] = mapped_column(String(50), default=TripStatus.CREATED)
    max_iterations: Mapped[int] = mapped_column(Integer, default=10)
    current_iteration: Mapped[int] = mapped_column(Integer, default=0)
    winner_itinerary_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "itineraries.id",
            name="fk_trips_winner_itinerary_id",
            ondelete="SET NULL",
            use_alter=True,
        )
    )
    notes: Mapped[str | None] = mapped_column(Text)
    generation_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
