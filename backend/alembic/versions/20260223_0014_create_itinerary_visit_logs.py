"""create itinerary visit logs

Revision ID: 20260223_0014
Revises: 192b2beb4568
Create Date: 2026-02-23 00:40:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260223_0014"
down_revision: str | None = "192b2beb4568"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "itinerary_visit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("itinerary_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("viewer_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("last_viewed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["itinerary_id"], ["itineraries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["viewer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "itinerary_id",
            "viewer_user_id",
            name="uq_itinerary_visit_logs_itinerary_viewer",
        ),
    )
    op.create_index(
        op.f("ix_itinerary_visit_logs_itinerary_id"),
        "itinerary_visit_logs",
        ["itinerary_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_itinerary_visit_logs_viewer_user_id"),
        "itinerary_visit_logs",
        ["viewer_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_itinerary_visit_logs_last_viewed_at"),
        "itinerary_visit_logs",
        ["last_viewed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_itinerary_visit_logs_last_viewed_at"), table_name="itinerary_visit_logs")
    op.drop_index(op.f("ix_itinerary_visit_logs_viewer_user_id"), table_name="itinerary_visit_logs")
    op.drop_index(op.f("ix_itinerary_visit_logs_itinerary_id"), table_name="itinerary_visit_logs")
    op.drop_table("itinerary_visit_logs")
