"""extend itinerary status and add cover image url

Revision ID: 20260218_0003
Revises: 20260218_0002
Create Date: 2026-02-18 15:30:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260218_0003"
down_revision: Union[str, None] = "20260218_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("itineraries", sa.Column("cover_image_url", sa.String(length=512), nullable=True))
    op.drop_constraint("ck_itineraries_status", "itineraries", type_="check")
    op.create_check_constraint(
        "ck_itineraries_status",
        "itineraries",
        "status IN ('draft', 'in_progress', 'published')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_itineraries_status", "itineraries", type_="check")
    op.create_check_constraint(
        "ck_itineraries_status",
        "itineraries",
        "status IN ('draft', 'published')",
    )
    op.drop_column("itineraries", "cover_image_url")
