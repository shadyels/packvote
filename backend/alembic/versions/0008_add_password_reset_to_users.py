"""add password reset columns to users

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-26

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("reset_token_hash", sa.String(64), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("reset_token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_users_reset_token_hash", "users", ["reset_token_hash"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_users_reset_token_hash", table_name="users")
    op.drop_column("users", "reset_token_expires_at")
    op.drop_column("users", "reset_token_hash")
