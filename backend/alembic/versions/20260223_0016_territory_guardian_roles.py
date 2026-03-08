"""territory guardian roles optimisation

Revision ID: 20260223_0016
Revises: 20260223_0015
Create Date: 2026-02-23
"""

from alembic import op
import sqlalchemy as sa


revision = "20260223_0016"
down_revision = "20260223_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- territory_guardians: add new columns ---
    op.add_column("territory_guardians", sa.Column("role", sa.String(20), nullable=False, server_default="regular"))
    op.add_column("territory_guardians", sa.Column("contribution_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("territory_guardians", sa.Column("thanks_received", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("territory_guardians", sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True))

    # Add role check constraint
    op.create_check_constraint(
        "ck_territory_guardians_role",
        "territory_guardians",
        "role IN ('regular', 'local_expert', 'area_guide', 'city_ambassador')",
    )

    # Update state check constraint: active/dormant/honorary (remove 'suspended')
    # Map existing 'suspended' guardians to 'active' before changing constraint
    op.execute("UPDATE territory_guardians SET state = 'active' WHERE state = 'suspended'")
    op.drop_constraint("ck_territory_guardians_state", "territory_guardians", type_="check")
    op.create_check_constraint(
        "ck_territory_guardians_state",
        "territory_guardians",
        "state IN ('active', 'dormant', 'honorary')",
    )

    # --- territory_guardian_activity_logs: expand action_type ---
    op.drop_constraint("ck_territory_guardian_activity_logs_action_type", "territory_guardian_activity_logs", type_="check")
    op.create_check_constraint(
        "ck_territory_guardian_activity_logs_action_type",
        "territory_guardian_activity_logs",
        "action_type IN ('check_in', 'review', 'correction_submit', 'verification', 'photo_upload', 'answer_question')",
    )

    # Widen action_type column to 24 chars (was 16)
    op.alter_column("territory_guardian_activity_logs", "action_type", type_=sa.String(24), existing_type=sa.String(16))

    # --- Drop reputation snapshots table ---
    op.drop_table("territory_guardian_reputation_snapshots")


def downgrade() -> None:
    # Recreate reputation snapshots table
    op.create_table(
        "territory_guardian_reputation_snapshots",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("territory_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("territory_regions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("guardian_user_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("window_size", sa.Integer(), nullable=False),
        sa.Column("reviewed_count", sa.Integer(), nullable=False),
        sa.Column("accepted_count", sa.Integer(), nullable=False),
        sa.Column("accuracy", sa.Float(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="ok"),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("territory_id", "guardian_user_id", name="uq_territory_guardian_reputation_snapshot"),
        sa.CheckConstraint("status IN ('ok', 'suspended')", name="ck_territory_guardian_reputation_snapshots_status"),
    )

    # Restore activity log constraint
    op.drop_constraint("ck_territory_guardian_activity_logs_action_type", "territory_guardian_activity_logs", type_="check")
    op.alter_column("territory_guardian_activity_logs", "action_type", type_=sa.String(16), existing_type=sa.String(24))
    op.create_check_constraint(
        "ck_territory_guardian_activity_logs_action_type",
        "territory_guardian_activity_logs",
        "action_type IN ('check_in', 'review')",
    )

    # Restore state constraint
    op.execute("UPDATE territory_guardians SET state = 'active' WHERE state = 'dormant'")
    op.drop_constraint("ck_territory_guardians_state", "territory_guardians", type_="check")
    op.create_check_constraint(
        "ck_territory_guardians_state",
        "territory_guardians",
        "state IN ('active', 'honorary', 'suspended')",
    )

    # Drop new columns and constraints
    op.drop_constraint("ck_territory_guardians_role", "territory_guardians", type_="check")
    op.drop_column("territory_guardians", "last_active_at")
    op.drop_column("territory_guardians", "thanks_received")
    op.drop_column("territory_guardians", "contribution_count")
    op.drop_column("territory_guardians", "role")
