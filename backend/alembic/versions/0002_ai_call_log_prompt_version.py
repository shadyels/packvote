"""ai_call_logs.prompt_version

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-19 12:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Inline stubs: the migration must not import app models, which change over time.
ai_call_logs = sa.table(
    "ai_call_logs",
    sa.column("trip_id", sa.Integer),
    sa.column("iteration_number", sa.Integer),
    sa.column("prompt_version", sa.String),
)
itineraries = sa.table(
    "itineraries",
    sa.column("trip_id", sa.Integer),
    sa.column("iteration_number", sa.Integer),
    sa.column("prompt_version", sa.String),
)


def upgrade() -> None:
    op.add_column(
        "ai_call_logs",
        sa.Column("prompt_version", sa.String(length=20), nullable=True),
    )
    # Backfill from the generation each attempt belonged to. Attempts of runs
    # that never produced an itinerary (and orphans) stay NULL.
    op.execute(
        sa.update(ai_call_logs).values(
            prompt_version=sa.select(itineraries.c.prompt_version)
            .where(
                itineraries.c.trip_id == ai_call_logs.c.trip_id,
                itineraries.c.iteration_number == ai_call_logs.c.iteration_number,
            )
            .limit(1)
            .scalar_subquery()
        )
    )


def downgrade() -> None:
    op.drop_column("ai_call_logs", "prompt_version")
