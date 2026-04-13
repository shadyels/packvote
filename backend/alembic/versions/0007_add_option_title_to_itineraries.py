"""add option_title to itineraries

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-13

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "itineraries",
        sa.Column("option_title", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("itineraries", "option_title")
