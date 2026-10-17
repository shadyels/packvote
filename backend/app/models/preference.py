from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, JSONType


class Preference(Base):
    __tablename__ = "preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    # One preference row per participant (submit_preferences upserts)
    participant_id: Mapped[int] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), unique=True
    )
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"))
    preferred_start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    preferred_end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    budget_min: Mapped[float | None] = mapped_column(Float)
    budget_max: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    interests: Mapped[str | None] = mapped_column(Text)  # free text
    activity_tags: Mapped[list[str] | None] = mapped_column(JSONType)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
