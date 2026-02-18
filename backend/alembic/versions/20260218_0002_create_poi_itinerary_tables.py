"""create poi and itinerary tables

Revision ID: 20260218_0002
Revises: 20260218_0001
Create Date: 2026-02-18 00:20:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.types import UserDefinedType

# revision identifiers, used by Alembic.
revision: str = "20260218_0002"
down_revision: Union[str, None] = "20260218_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


class GeometryPoint(UserDefinedType):
    def get_col_spec(self, **kw: object) -> str:
        return "GEOMETRY(Point,4326)"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "pois",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("geom", GeometryPoint(), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("opening_hours", sa.String(length=255), nullable=True),
        sa.Column("ticket_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("parent_poi_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["parent_poi_id"], ["pois.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pois_name", "pois", ["name"], unique=False)

    op.create_table(
        "itineraries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("destination", sa.String(length=64), nullable=False),
        sa.Column("days", sa.Integer(), nullable=False),
        sa.Column("creator_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("visibility", sa.String(length=16), nullable=False, server_default="private"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("days > 0", name="ck_itineraries_days_positive"),
        sa.CheckConstraint("status IN ('draft', 'published')", name="ck_itineraries_status"),
        sa.CheckConstraint(
            "visibility IN ('private', 'public', 'followers')", name="ck_itineraries_visibility"
        ),
        sa.ForeignKeyConstraint(["creator_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_itineraries_creator_user_id", "itineraries", ["creator_user_id"], unique=False)

    op.create_table(
        "itinerary_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("itinerary_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day_index", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("poi_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("cost", sa.Numeric(10, 2), nullable=True),
        sa.Column("tips", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["itinerary_id"], ["itineraries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["poi_id"], ["pois.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("itinerary_id", "day_index", "sort_order", name="uq_itinerary_day_sort"),
    )
    op.create_index("ix_itinerary_items_itinerary_id", "itinerary_items", ["itinerary_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_itinerary_items_itinerary_id", table_name="itinerary_items")
    op.drop_table("itinerary_items")
    op.drop_index("ix_itineraries_creator_user_id", table_name="itineraries")
    op.drop_table("itineraries")
    op.drop_index("ix_pois_name", table_name="pois")
    op.drop_table("pois")
