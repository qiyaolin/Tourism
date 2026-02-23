"""create territory guardian tables

Revision ID: 20260223_0015
Revises: 20260223_0014
Create Date: 2026-02-23 15:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import UserDefinedType

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260223_0015"
down_revision: str | None = "20260223_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


class GeometryPoint(UserDefinedType):
    def get_col_spec(self, **kw: object) -> str:
        return "GEOMETRY(Point,4326)"


class GeometryPolygon(UserDefinedType):
    def get_col_spec(self, **kw: object) -> str:
        return "GEOMETRY(Polygon,4326)"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "territory_regions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("boundary_geom", GeometryPolygon(), nullable=False),
        sa.Column("centroid_geom", GeometryPoint(), nullable=False),
        sa.Column("poi_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('active', 'inactive')", name="ck_territory_regions_status"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_territory_regions_code"), "territory_regions", ["code"], unique=True)
    op.create_index(
        "ix_territory_regions_boundary_geom_gist",
        "territory_regions",
        ["boundary_geom"],
        unique=False,
        postgresql_using="gist",
    )

    op.create_table(
        "territory_guardian_applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("territory_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("applicant_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("reviewer_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_territory_guardian_applications_status",
        ),
        sa.ForeignKeyConstraint(["territory_id"], ["territory_regions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["applicant_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_territory_guardian_applications_territory_id"),
        "territory_guardian_applications",
        ["territory_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_territory_guardian_applications_applicant_user_id"),
        "territory_guardian_applications",
        ["applicant_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_territory_guardian_applications_reviewer_user_id"),
        "territory_guardian_applications",
        ["reviewer_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_territory_guardian_applications_status"),
        "territory_guardian_applications",
        ["status"],
        unique=False,
    )
    op.create_index(
        "uq_territory_guardian_applications_pending_once",
        "territory_guardian_applications",
        ["territory_id", "applicant_user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )

    op.create_table(
        "territory_guardians",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("territory_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("granted_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "state IN ('active', 'honorary', 'suspended')",
            name="ck_territory_guardians_state",
        ),
        sa.ForeignKeyConstraint(["territory_id"], ["territory_regions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["granted_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["revoked_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("territory_id", "user_id", name="uq_territory_guardians_territory_user"),
    )
    op.create_index(op.f("ix_territory_guardians_territory_id"), "territory_guardians", ["territory_id"], unique=False)
    op.create_index(op.f("ix_territory_guardians_user_id"), "territory_guardians", ["user_id"], unique=False)
    op.create_index(op.f("ix_territory_guardians_state"), "territory_guardians", ["state"], unique=False)

    op.create_table(
        "territory_guardian_activity_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("territory_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("guardian_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_type", sa.String(length=16), nullable=False),
        sa.Column("related_correction_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "action_type IN ('check_in', 'review')",
            name="ck_territory_guardian_activity_logs_action_type",
        ),
        sa.ForeignKeyConstraint(["territory_id"], ["territory_regions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["guardian_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["related_correction_id"], ["poi_corrections.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_territory_guardian_activity_logs_territory_id"),
        "territory_guardian_activity_logs",
        ["territory_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_territory_guardian_activity_logs_guardian_user_id"),
        "territory_guardian_activity_logs",
        ["guardian_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_territory_guardian_activity_logs_related_correction_id"),
        "territory_guardian_activity_logs",
        ["related_correction_id"],
        unique=False,
    )
    op.create_index(
        "ix_tgal_guardian_territory_created_at",
        "territory_guardian_activity_logs",
        ["guardian_user_id", "territory_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "territory_guardian_reputation_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("territory_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("guardian_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("window_size", sa.Integer(), nullable=False),
        sa.Column("reviewed_count", sa.Integer(), nullable=False),
        sa.Column("accepted_count", sa.Integer(), nullable=False),
        sa.Column("accuracy", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="ok"),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('ok', 'suspended')",
            name="ck_territory_guardian_reputation_snapshots_status",
        ),
        sa.ForeignKeyConstraint(["territory_id"], ["territory_regions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["guardian_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "territory_id",
            "guardian_user_id",
            name="uq_territory_guardian_reputation_snapshot",
        ),
    )
    op.create_index(
        op.f("ix_territory_guardian_reputation_snapshots_territory_id"),
        "territory_guardian_reputation_snapshots",
        ["territory_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_territory_guardian_reputation_snapshots_guardian_user_id"),
        "territory_guardian_reputation_snapshots",
        ["guardian_user_id"],
        unique=False,
    )

    op.add_column("pois", sa.Column("territory_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_pois_territory_id_territory_regions",
        "pois",
        "territory_regions",
        ["territory_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_pois_territory_id"), "pois", ["territory_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_pois_territory_id"), table_name="pois")
    op.drop_constraint("fk_pois_territory_id_territory_regions", "pois", type_="foreignkey")
    op.drop_column("pois", "territory_id")

    op.drop_index(
        op.f("ix_territory_guardian_reputation_snapshots_guardian_user_id"),
        table_name="territory_guardian_reputation_snapshots",
    )
    op.drop_index(
        op.f("ix_territory_guardian_reputation_snapshots_territory_id"),
        table_name="territory_guardian_reputation_snapshots",
    )
    op.drop_table("territory_guardian_reputation_snapshots")

    op.drop_index("ix_tgal_guardian_territory_created_at", table_name="territory_guardian_activity_logs")
    op.drop_index(
        op.f("ix_territory_guardian_activity_logs_related_correction_id"),
        table_name="territory_guardian_activity_logs",
    )
    op.drop_index(
        op.f("ix_territory_guardian_activity_logs_guardian_user_id"),
        table_name="territory_guardian_activity_logs",
    )
    op.drop_index(
        op.f("ix_territory_guardian_activity_logs_territory_id"),
        table_name="territory_guardian_activity_logs",
    )
    op.drop_table("territory_guardian_activity_logs")

    op.drop_index(op.f("ix_territory_guardians_state"), table_name="territory_guardians")
    op.drop_index(op.f("ix_territory_guardians_user_id"), table_name="territory_guardians")
    op.drop_index(op.f("ix_territory_guardians_territory_id"), table_name="territory_guardians")
    op.drop_table("territory_guardians")

    op.drop_index("uq_territory_guardian_applications_pending_once", table_name="territory_guardian_applications")
    op.drop_index(op.f("ix_territory_guardian_applications_status"), table_name="territory_guardian_applications")
    op.drop_index(
        op.f("ix_territory_guardian_applications_reviewer_user_id"),
        table_name="territory_guardian_applications",
    )
    op.drop_index(
        op.f("ix_territory_guardian_applications_applicant_user_id"),
        table_name="territory_guardian_applications",
    )
    op.drop_index(
        op.f("ix_territory_guardian_applications_territory_id"),
        table_name="territory_guardian_applications",
    )
    op.drop_table("territory_guardian_applications")

    op.drop_index("ix_territory_regions_boundary_geom_gist", table_name="territory_regions")
    op.drop_index(op.f("ix_territory_regions_code"), table_name="territory_regions")
    op.drop_table("territory_regions")
