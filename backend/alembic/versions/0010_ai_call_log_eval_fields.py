"""add evaluation fields to ai_call_logs

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-14

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ai_call_logs", sa.Column("prompt", sa.Text(), nullable=True))
    op.add_column(
        "ai_call_logs", sa.Column("finish_reason", sa.String(50), nullable=True)
    )
    op.add_column(
        "ai_call_logs", sa.Column("token_count_total", sa.Integer(), nullable=True)
    )
    op.add_column("ai_call_logs", sa.Column("attempt", sa.Integer(), nullable=True))
    op.add_column(
        "ai_call_logs", sa.Column("iteration_number", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("ai_call_logs", "iteration_number")
    op.drop_column("ai_call_logs", "attempt")
    op.drop_column("ai_call_logs", "token_count_total")
    op.drop_column("ai_call_logs", "finish_reason")
    op.drop_column("ai_call_logs", "prompt")
