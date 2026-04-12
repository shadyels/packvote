"""drop votes.user_id — column became write-dead after creator-as-participant

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-12

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("votes_user_id_fkey", "votes", type_="foreignkey")
    op.drop_column("votes", "user_id")


def downgrade() -> None:
    op.add_column(
        "votes",
        sa.Column("user_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "votes_user_id_fkey",
        "votes",
        "users",
        ["user_id"],
        ["id"],
    )
