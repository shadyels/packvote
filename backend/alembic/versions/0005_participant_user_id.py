"""add user_id FK to participants

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-11

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "participants",
        sa.Column("user_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_participants_user_id",
        "participants",
        "users",
        ["user_id"],
        ["id"],
    )
    op.create_index("ix_participants_user_id", "participants", ["user_id"])
    op.create_index(
        "uq_participants_trip_user",
        "participants",
        ["trip_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_participants_trip_user", table_name="participants")
    op.drop_index("ix_participants_user_id", table_name="participants")
    op.drop_constraint("fk_participants_user_id", "participants", type_="foreignkey")
    op.drop_column("participants", "user_id")
