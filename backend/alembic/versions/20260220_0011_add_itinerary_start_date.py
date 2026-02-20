"""add start_date to itineraries

Revision ID: 20260220_0011
Revises: 20260220_0010
Create Date: 2026-02-20 16:05:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260220_0011"
down_revision: str | None = "20260220_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("itineraries", sa.Column("start_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("itineraries", "start_date")
