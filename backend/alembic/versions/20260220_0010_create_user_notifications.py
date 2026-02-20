"""create user notifications table

Revision ID: 20260220_0010
Revises: 20260220_0009
Create Date: 2026-02-20 13:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260220_0010"
down_revision: str | None = "20260220_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipient_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("content", sa.String(length=500), nullable=False),
        sa.Column("is_read", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_itinerary_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("forked_itinerary_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("correction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("poi_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "extra_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("dedupe_key", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('source_itinerary_updated', 'correction_accepted')",
            name="ck_user_notifications_event_type",
        ),
        sa.CheckConstraint(
            "severity IN ('critical', 'warning', 'info')",
            name="ck_user_notifications_severity",
        ),
        sa.ForeignKeyConstraint(["correction_id"], ["poi_corrections.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["forked_itinerary_id"], ["itineraries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["poi_id"], ["pois.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_itinerary_id"], ["itineraries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_snapshot_id"], ["itinerary_snapshots.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key", name="uq_user_notifications_dedupe_key"),
    )
    op.create_index(
        "ix_user_notifications_recipient_is_read_created_at",
        "user_notifications",
        ["recipient_user_id", "is_read", "created_at"],
        unique=False,
    )
    op.create_index("ix_user_notifications_event_type", "user_notifications", ["event_type"], unique=False)
    op.create_index("ix_user_notifications_recipient_user_id", "user_notifications", ["recipient_user_id"], unique=False)
    op.create_index("ix_user_notifications_sender_user_id", "user_notifications", ["sender_user_id"], unique=False)
    op.create_index("ix_user_notifications_source_itinerary_id", "user_notifications", ["source_itinerary_id"], unique=False)
    op.create_index("ix_user_notifications_forked_itinerary_id", "user_notifications", ["forked_itinerary_id"], unique=False)
    op.create_index("ix_user_notifications_source_snapshot_id", "user_notifications", ["source_snapshot_id"], unique=False)
    op.create_index("ix_user_notifications_correction_id", "user_notifications", ["correction_id"], unique=False)
    op.create_index("ix_user_notifications_poi_id", "user_notifications", ["poi_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_notifications_poi_id", table_name="user_notifications")
    op.drop_index("ix_user_notifications_correction_id", table_name="user_notifications")
    op.drop_index("ix_user_notifications_source_snapshot_id", table_name="user_notifications")
    op.drop_index("ix_user_notifications_forked_itinerary_id", table_name="user_notifications")
    op.drop_index("ix_user_notifications_source_itinerary_id", table_name="user_notifications")
    op.drop_index("ix_user_notifications_sender_user_id", table_name="user_notifications")
    op.drop_index("ix_user_notifications_recipient_user_id", table_name="user_notifications")
    op.drop_index("ix_user_notifications_event_type", table_name="user_notifications")
    op.drop_index("ix_user_notifications_recipient_is_read_created_at", table_name="user_notifications")
    op.drop_table("user_notifications")
