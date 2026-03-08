"""create bounty task tables

Revision ID: 20260225_0017
Revises: 20260223_0016
Create Date: 2026-02-25 14:40:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260225_0017"
down_revision: str | None = "20260223_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bounty_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("poi_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("territory_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
        sa.Column("reward_points", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("stale_days_snapshot", sa.Integer(), nullable=False, server_default="45"),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('open', 'claimed', 'submitted', 'approved', 'rejected', 'expired')",
            name="ck_bounty_tasks_status",
        ),
        sa.CheckConstraint("reward_points >= 0", name="ck_bounty_tasks_reward_points_nonnegative"),
        sa.CheckConstraint("stale_days_snapshot >= 0", name="ck_bounty_tasks_stale_days_nonnegative"),
        sa.ForeignKeyConstraint(["poi_id"], ["pois.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["territory_id"], ["territory_regions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["claimed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bounty_tasks_poi_id"), "bounty_tasks", ["poi_id"], unique=False)
    op.create_index(op.f("ix_bounty_tasks_territory_id"), "bounty_tasks", ["territory_id"], unique=False)
    op.create_index(op.f("ix_bounty_tasks_status"), "bounty_tasks", ["status"], unique=False)
    op.create_index(op.f("ix_bounty_tasks_claimed_by_user_id"), "bounty_tasks", ["claimed_by_user_id"], unique=False)
    op.create_index(op.f("ix_bounty_tasks_approved_by_user_id"), "bounty_tasks", ["approved_by_user_id"], unique=False)
    op.create_index(
        "ix_bounty_tasks_status_generated_at",
        "bounty_tasks",
        ["status", "generated_at"],
        unique=False,
    )
    op.create_index(
        "ix_bounty_tasks_poi_status",
        "bounty_tasks",
        ["poi_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_bounty_tasks_claimed_by_user_created_at",
        "bounty_tasks",
        ["claimed_by_user_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "bounty_submissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submitter_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submit_longitude", sa.Numeric(precision=10, scale=7), nullable=False),
        sa.Column("submit_latitude", sa.Numeric(precision=10, scale=7), nullable=False),
        sa.Column("distance_meters", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("gps_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("photo_url", sa.String(length=512), nullable=True),
        sa.Column("photo_storage_key", sa.String(length=512), nullable=True),
        sa.Column("photo_exif_captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("photo_exif_longitude", sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column("photo_exif_latitude", sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("risk_level", sa.String(length=16), nullable=False, server_default="normal"),
        sa.Column("review_status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("reviewer_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("distance_meters >= 0", name="ck_bounty_submissions_distance_nonnegative"),
        sa.CheckConstraint(
            "submit_longitude BETWEEN -180 AND 180",
            name="ck_bounty_submissions_longitude_range",
        ),
        sa.CheckConstraint("submit_latitude BETWEEN -90 AND 90", name="ck_bounty_submissions_latitude_range"),
        sa.CheckConstraint(
            "review_status IN ('pending', 'approved', 'rejected')",
            name="ck_bounty_submissions_review_status",
        ),
        sa.CheckConstraint(
            "risk_level IN ('normal', 'manual_review')",
            name="ck_bounty_submissions_risk_level",
        ),
        sa.ForeignKeyConstraint(["task_id"], ["bounty_tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submitter_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", name="uq_bounty_submissions_task_id"),
    )
    op.create_index(op.f("ix_bounty_submissions_task_id"), "bounty_submissions", ["task_id"], unique=True)
    op.create_index(
        op.f("ix_bounty_submissions_submitter_user_id"),
        "bounty_submissions",
        ["submitter_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_bounty_submissions_reviewer_user_id"),
        "bounty_submissions",
        ["reviewer_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_bounty_submissions_review_status"),
        "bounty_submissions",
        ["review_status"],
        unique=False,
    )
    op.create_index(
        "ix_bounty_submissions_submitter_created_at",
        "bounty_submissions",
        ["submitter_user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_bounty_submissions_submitter_created_at", table_name="bounty_submissions")
    op.drop_index(op.f("ix_bounty_submissions_review_status"), table_name="bounty_submissions")
    op.drop_index(op.f("ix_bounty_submissions_reviewer_user_id"), table_name="bounty_submissions")
    op.drop_index(op.f("ix_bounty_submissions_submitter_user_id"), table_name="bounty_submissions")
    op.drop_index(op.f("ix_bounty_submissions_task_id"), table_name="bounty_submissions")
    op.drop_table("bounty_submissions")

    op.drop_index("ix_bounty_tasks_claimed_by_user_created_at", table_name="bounty_tasks")
    op.drop_index("ix_bounty_tasks_poi_status", table_name="bounty_tasks")
    op.drop_index("ix_bounty_tasks_status_generated_at", table_name="bounty_tasks")
    op.drop_index(op.f("ix_bounty_tasks_approved_by_user_id"), table_name="bounty_tasks")
    op.drop_index(op.f("ix_bounty_tasks_claimed_by_user_id"), table_name="bounty_tasks")
    op.drop_index(op.f("ix_bounty_tasks_status"), table_name="bounty_tasks")
    op.drop_index(op.f("ix_bounty_tasks_territory_id"), table_name="bounty_tasks")
    op.drop_index(op.f("ix_bounty_tasks_poi_id"), table_name="bounty_tasks")
    op.drop_table("bounty_tasks")
