"""convert json text columns to jsonb and rename

Revision ID: 0009
Revises: 0008
Create Date: 2026-04-27

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    if is_pg:
        op.execute(
            "ALTER TABLE votes ALTER COLUMN rankings_json TYPE JSONB USING rankings_json::jsonb"
        )
        op.execute(
            "ALTER TABLE vote_rounds ALTER COLUMN results_json TYPE JSONB USING results_json::jsonb"
        )
        op.execute(
            "ALTER TABLE itineraries ALTER COLUMN daily_itinerary_json TYPE JSONB USING daily_itinerary_json::jsonb"
        )
        op.execute(
            "ALTER TABLE itineraries ALTER COLUMN highlights TYPE JSONB USING highlights::jsonb"
        )
        op.execute(
            "ALTER TABLE preferences ALTER COLUMN activity_tags TYPE JSONB USING activity_tags::jsonb"
        )
    # SQLite: type is advisory; SQLAlchemy JSON roundtrips through TEXT automatically

    op.alter_column("votes", "rankings_json", new_column_name="rankings")
    op.alter_column("vote_rounds", "results_json", new_column_name="results")
    op.alter_column(
        "itineraries", "daily_itinerary_json", new_column_name="daily_itinerary"
    )


def downgrade() -> None:
    op.alter_column("votes", "rankings", new_column_name="rankings_json")
    op.alter_column("vote_rounds", "results", new_column_name="results_json")
    op.alter_column(
        "itineraries", "daily_itinerary", new_column_name="daily_itinerary_json"
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "ALTER TABLE votes ALTER COLUMN rankings_json TYPE TEXT USING rankings_json::text"
        )
        op.execute(
            "ALTER TABLE vote_rounds ALTER COLUMN results_json TYPE TEXT USING results_json::text"
        )
        op.execute(
            "ALTER TABLE itineraries ALTER COLUMN daily_itinerary_json TYPE TEXT USING daily_itinerary_json::text"
        )
        op.execute(
            "ALTER TABLE itineraries ALTER COLUMN highlights TYPE TEXT USING highlights::text"
        )
        op.execute(
            "ALTER TABLE preferences ALTER COLUMN activity_tags TYPE TEXT USING activity_tags::text"
        )
