"""create poi correction tables

Revision ID: 20260219_0006
Revises: 20260219_0005
Create Date: 2026-02-19 09:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260219_0006"
down_revision: str | None = "20260219_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "poi_correction_types",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=64), nullable=False),
        sa.Column("target_field", sa.String(length=64), nullable=False),
        sa.Column("value_kind", sa.String(length=16), nullable=False),
        sa.Column("placeholder", sa.String(length=255), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_poi_correction_types_code", "poi_correction_types", ["code"], unique=True)

    op.create_table(
        "poi_corrections",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("poi_id", sa.UUID(), nullable=False),
        sa.Column("type_id", sa.UUID(), nullable=False),
        sa.Column("submitter_user_id", sa.UUID(), nullable=False),
        sa.Column("reviewer_user_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("proposed_value", sa.Text(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("photo_url", sa.String(length=512), nullable=True),
        sa.Column("photo_storage_key", sa.String(length=512), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("before_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["poi_id"], ["pois.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["type_id"], ["poi_correction_types.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["submitter_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected')",
            name="ck_poi_corrections_status",
        ),
    )
    op.create_index("ix_poi_corrections_poi_id", "poi_corrections", ["poi_id"], unique=False)
    op.create_index("ix_poi_corrections_type_id", "poi_corrections", ["type_id"], unique=False)
    op.create_index("ix_poi_corrections_submitter_user_id", "poi_corrections", ["submitter_user_id"], unique=False)
    op.create_index("ix_poi_corrections_reviewer_user_id", "poi_corrections", ["reviewer_user_id"], unique=False)
    op.create_index("ix_poi_corrections_status", "poi_corrections", ["status"], unique=False)

    op.create_table(
        "poi_correction_notifications",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("correction_id", sa.UUID(), nullable=False),
        sa.Column("recipient_user_id", sa.UUID(), nullable=False),
        sa.Column("sender_user_id", sa.UUID(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["correction_id"], ["poi_corrections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_poi_correction_notifications_correction_id",
        "poi_correction_notifications",
        ["correction_id"],
        unique=False,
    )
    op.create_index(
        "ix_poi_correction_notifications_recipient_user_id",
        "poi_correction_notifications",
        ["recipient_user_id"],
        unique=False,
    )

    op.execute(
        """
        INSERT INTO poi_correction_types (id, code, label, target_field, value_kind, placeholder, sort_order, is_active)
        VALUES
            ('e6eb9f2e-f4dc-45eb-bbe5-6546f339c003', 'ticket_price_changed', '票价信息有误', 'ticket_price', 'number', '例如：120', 10, true),
            ('30f479b7-14a7-4713-b497-2eb30f43f7f6', 'opening_hours_changed', '营业时间变更', 'opening_hours', 'string', '例如：09:00-18:00', 20, false),
            ('96de59ee-f2f9-4ef7-9f96-c9180574dcad', 'address_changed', '地址信息有误', 'address', 'string', '请填写更准确的地址', 30, false),
            ('20451f01-d742-40e2-97c9-4c94fa50f237', 'temporary_closed', '临时闭园', 'opening_hours', 'string', '例如：临时停业至 2026-03-01', 40, false),
            ('988fc14f-b60f-4332-ba7d-8acc914ed94d', 'other', '其他', 'address', 'string', '请描述你发现的问题', 90, false)
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_poi_correction_notifications_recipient_user_id",
        table_name="poi_correction_notifications",
    )
    op.drop_index(
        "ix_poi_correction_notifications_correction_id",
        table_name="poi_correction_notifications",
    )
    op.drop_table("poi_correction_notifications")

    op.drop_index("ix_poi_corrections_status", table_name="poi_corrections")
    op.drop_index("ix_poi_corrections_reviewer_user_id", table_name="poi_corrections")
    op.drop_index("ix_poi_corrections_submitter_user_id", table_name="poi_corrections")
    op.drop_index("ix_poi_corrections_type_id", table_name="poi_corrections")
    op.drop_index("ix_poi_corrections_poi_id", table_name="poi_corrections")
    op.drop_table("poi_corrections")

    op.drop_index("ix_poi_correction_types_code", table_name="poi_correction_types")
    op.drop_table("poi_correction_types")
