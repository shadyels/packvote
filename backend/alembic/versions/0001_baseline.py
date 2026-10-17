"""baseline

Revision ID: 0001
Revises:
Create Date: 2026-10-17 19:38:28.855606

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reset_token_hash", sa.String(length=64), nullable=True),
        sa.Column("reset_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("reset_token_hash"),
    )
    op.create_table(
        "trips",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trip_code", sa.String(length=8), nullable=False),
        sa.Column("creator_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("destination", sa.String(length=255), nullable=True),
        sa.Column("proposed_start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("proposed_end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("num_options", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("max_iterations", sa.Integer(), nullable=False),
        sa.Column("current_iteration", sa.Integer(), nullable=False),
        sa.Column("winner_itinerary_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("generation_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["creator_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trip_code"),
    )
    op.create_index(op.f("ix_trips_creator_id"), "trips", ["creator_id"], unique=False)
    op.create_table(
        "ai_call_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trip_id", sa.Integer(), nullable=True),
        sa.Column("iteration_number", sa.Integer(), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=True),
        sa.Column("model_used", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("token_count_input", sa.Integer(), nullable=True),
        sa.Column("token_count_output", sa.Integer(), nullable=True),
        sa.Column("token_count_total", sa.Integer(), nullable=True),
        sa.Column("finish_reason", sa.String(length=50), nullable=True),
        sa.Column("response_valid", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("raw_response", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ai_call_logs_trip_id"), "ai_call_logs", ["trip_id"], unique=False
    )
    op.create_table(
        "itineraries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trip_id", sa.Integer(), nullable=False),
        sa.Column("iteration_number", sa.Integer(), nullable=False),
        sa.Column("option_title", sa.String(length=255), nullable=True),
        sa.Column("destination_name", sa.String(length=255), nullable=False),
        sa.Column("destination_description", sa.Text(), nullable=False),
        sa.Column(
            "daily_itinerary",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=False,
        ),
        sa.Column("total_estimated_budget", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("match_reasoning", sa.Text(), nullable=False),
        sa.Column(
            "highlights",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=False,
        ),
        sa.Column("prompt_version", sa.String(length=20), nullable=True),
        sa.Column("model_used", sa.String(length=255), nullable=True),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("generation_latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_itineraries_trip_id"), "itineraries", ["trip_id"], unique=False
    )
    # trips <-> itineraries is circular: add this FK once itineraries exists
    op.create_foreign_key(
        "fk_trips_winner_itinerary_id",
        "trips",
        "itineraries",
        ["winner_itinerary_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_table(
        "participants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trip_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("pin", sa.String(length=4), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("preferences_submitted", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
        sa.UniqueConstraint("trip_id", "pin", name="uq_participants_trip_id_pin"),
    )
    op.create_index(
        op.f("ix_participants_user_id"), "participants", ["user_id"], unique=False
    )
    op.create_index(
        "uq_participants_trip_user",
        "participants",
        ["trip_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL"),
        sqlite_where=sa.text("user_id IS NOT NULL"),
    )
    op.create_table(
        "preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("participant_id", sa.Integer(), nullable=False),
        sa.Column("trip_id", sa.Integer(), nullable=False),
        sa.Column("preferred_start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("preferred_end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("budget_min", sa.Float(), nullable=True),
        sa.Column("budget_max", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("interests", sa.Text(), nullable=True),
        sa.Column(
            "activity_tags",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=True,
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["participant_id"], ["participants.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("participant_id"),
    )
    op.create_table(
        "votes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("participant_id", sa.Integer(), nullable=False),
        sa.Column("trip_id", sa.Integer(), nullable=False),
        sa.Column("iteration_number", sa.Integer(), nullable=False),
        sa.Column(
            "rankings",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=False,
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["participant_id"], ["participants.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "trip_id",
            "iteration_number",
            "participant_id",
            name="uq_votes_trip_iteration_participant",
        ),
    )


def downgrade() -> None:
    op.drop_table("votes")
    op.drop_table("preferences")
    op.drop_index(
        "uq_participants_trip_user",
        table_name="participants",
        postgresql_where=sa.text("user_id IS NOT NULL"),
        sqlite_where=sa.text("user_id IS NOT NULL"),
    )
    op.drop_index(op.f("ix_participants_user_id"), table_name="participants")
    op.drop_table("participants")
    op.drop_index(op.f("ix_itineraries_trip_id"), table_name="itineraries")
    op.drop_constraint("fk_trips_winner_itinerary_id", "trips", type_="foreignkey")
    op.drop_table("itineraries")
    op.drop_index(op.f("ix_ai_call_logs_trip_id"), table_name="ai_call_logs")
    op.drop_table("ai_call_logs")
    op.drop_index(op.f("ix_trips_creator_id"), table_name="trips")
    op.drop_table("trips")
    op.drop_table("users")
