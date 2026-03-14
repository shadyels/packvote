"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-14

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("template_text", sa.Text(), nullable=False),
        sa.Column("model_target", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("ab_test_group", sa.String(50), nullable=True),
        sa.Column("traffic_weight", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "trips",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trip_code", sa.String(8), nullable=False),
        sa.Column("pin", sa.String(4), nullable=False),
        sa.Column("creator_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("destination", sa.String(255), nullable=True),
        sa.Column("proposed_start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("proposed_end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("num_options", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("max_iterations", sa.Integer(), nullable=False),
        sa.Column("current_iteration", sa.Integer(), nullable=False),
        sa.Column("winner_itinerary_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trip_code"),
    )
    op.create_index("ix_trips_trip_code", "trips", ["trip_code"])

    op.create_table(
        "itineraries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trip_id", sa.Integer(), nullable=False),
        sa.Column("iteration_number", sa.Integer(), nullable=False),
        sa.Column("destination_name", sa.String(255), nullable=False),
        sa.Column("destination_description", sa.Text(), nullable=False),
        sa.Column("daily_itinerary_json", sa.Text(), nullable=False),
        sa.Column("total_estimated_budget", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("match_reasoning", sa.Text(), nullable=False),
        sa.Column("highlights", sa.Text(), nullable=False),
        sa.Column("prompt_version_id", sa.Integer(), nullable=True),
        sa.Column("model_used", sa.String(255), nullable=True),
        sa.Column("provider", sa.String(100), nullable=True),
        sa.Column("generation_latency_ms", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Float(), nullable=True),
        sa.Column("price_last_updated", sa.DateTime(timezone=True), nullable=True),
        sa.Column("price_source", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"]),
        sa.ForeignKeyConstraint(["prompt_version_id"], ["prompt_templates.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Now that itineraries table exists, add the FK from trips.winner_itinerary_id
    op.create_foreign_key(
        "fk_trips_winner_itinerary_id",
        "trips",
        "itineraries",
        ["winner_itinerary_id"],
        ["id"],
    )

    op.create_table(
        "participants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trip_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("token", sa.String(255), nullable=False),
        sa.Column("preferences_submitted", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_participants_token", "participants", ["token"])

    op.create_table(
        "preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("participant_id", sa.Integer(), nullable=False),
        sa.Column("trip_id", sa.Integer(), nullable=False),
        sa.Column("preferred_start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("preferred_end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("budget_min", sa.Float(), nullable=True),
        sa.Column("budget_max", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("interests", sa.Text(), nullable=True),
        sa.Column("activity_tags", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"]),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "votes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("participant_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("trip_id", sa.Integer(), nullable=False),
        sa.Column("iteration_number", sa.Integer(), nullable=False),
        sa.Column("rankings_json", sa.Text(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "vote_rounds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trip_id", sa.Integer(), nullable=False),
        sa.Column("iteration_number", sa.Integer(), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("eliminated_option_id", sa.Integer(), nullable=True),
        sa.Column("results_json", sa.Text(), nullable=False),
        sa.Column("winner_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"]),
        sa.ForeignKeyConstraint(["eliminated_option_id"], ["itineraries.id"]),
        sa.ForeignKeyConstraint(["winner_id"], ["itineraries.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "ai_call_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trip_id", sa.Integer(), nullable=True),
        sa.Column("prompt_version_id", sa.Integer(), nullable=True),
        sa.Column("model_used", sa.String(255), nullable=False),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("token_count_input", sa.Integer(), nullable=True),
        sa.Column("token_count_output", sa.Integer(), nullable=True),
        sa.Column("response_valid", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"]),
        sa.ForeignKeyConstraint(["prompt_version_id"], ["prompt_templates.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("ai_call_logs")
    op.drop_table("vote_rounds")
    op.drop_table("votes")
    op.drop_table("preferences")
    op.drop_index("ix_participants_token", "participants")
    op.drop_table("participants")
    op.drop_constraint("fk_trips_winner_itinerary_id", "trips", type_="foreignkey")
    op.drop_table("itineraries")
    op.drop_index("ix_trips_trip_code", "trips")
    op.drop_table("trips")
    op.drop_table("prompt_templates")
    op.drop_index("ix_users_email", "users")
    op.drop_table("users")
