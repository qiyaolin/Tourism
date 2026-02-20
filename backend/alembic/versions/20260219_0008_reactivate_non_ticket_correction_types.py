"""reactivate non-ticket correction types

Revision ID: 20260219_0008
Revises: 20260219_0007
Create Date: 2026-02-19 17:15:00
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260219_0008"
down_revision: str | None = "20260219_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE poi_correction_types
        SET is_active = true
        WHERE code IN (
            'ticket_price_changed',
            'opening_hours_changed',
            'address_changed',
            'temporary_closed',
            'other'
        )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE poi_correction_types
        SET is_active = CASE
            WHEN code = 'ticket_price_changed' THEN true
            ELSE false
        END
        WHERE code IN (
            'ticket_price_changed',
            'opening_hours_changed',
            'address_changed',
            'temporary_closed',
            'other'
        )
        """
    )
