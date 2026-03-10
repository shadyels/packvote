from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    token: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    preferences_submitted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    trip: Mapped[Trip] = relationship("Trip", back_populates="participants")  # type: ignore[name-defined]
    preferences: Mapped[list[Preference]] = relationship(
        "Preference", back_populates="participant"
    )  # type: ignore[name-defined]
    votes: Mapped[list[Vote]] = relationship("Vote", back_populates="participant")  # type: ignore[name-defined]
