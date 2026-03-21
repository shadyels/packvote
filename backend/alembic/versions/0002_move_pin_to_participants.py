"""move pin from trips to participants

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-21

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add pin column to participants (nullable first for data migration)
    op.add_column("participants", sa.Column("pin", sa.String(4), nullable=True))

    # Copy trip.pin to all related participants.pin
    op.execute(
        """
        UPDATE participants
        SET pin = trips.pin
        FROM trips
        WHERE participants.trip_id = trips.id
        """
    )

    # Make pin non-nullable
    op.alter_column("participants", "pin", nullable=False)

    # Add unique constraint on (trip_id, pin) — PIN must be unique within a trip
    op.create_unique_constraint(
        "uq_participants_trip_id_pin", "participants", ["trip_id", "pin"]
    )

    # Drop pin from trips
    op.drop_column("trips", "pin")


def downgrade() -> None:
    # Restore pin on trips (use a placeholder — original values are lost)
    op.add_column("trips", sa.Column("pin", sa.String(4), nullable=True))

    # Populate with the first participant's pin per trip as a best-effort restore
    op.execute(
        """
        UPDATE trips
        SET pin = (
            SELECT pin FROM participants
            WHERE participants.trip_id = trips.id
            LIMIT 1
        )
        """
    )

    op.alter_column("trips", "pin", nullable=False)

    # Remove unique constraint and pin from participants
    op.drop_constraint("uq_participants_trip_id_pin", "participants", type_="unique")
    op.drop_column("participants", "pin")
