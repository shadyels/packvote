"""add raw_response to ai_call_logs

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-22

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ai_call_logs",
        sa.Column("raw_response", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ai_call_logs", "raw_response")
