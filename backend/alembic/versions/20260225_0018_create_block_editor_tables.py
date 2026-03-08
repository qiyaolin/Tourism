"""create block editor tables

Revision ID: 20260225_0018
Revises: 20260225_0017
Create Date: 2026-02-25
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260225_0018"
down_revision = "20260225_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- block_templates (must be created before itinerary_blocks due to FK) ---
    op.create_table(
        "block_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("style_tags", postgresql.JSON, nullable=True),
        sa.Column("block_type", sa.String(32), nullable=False),
        sa.Column("is_group", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("content_snapshot", postgresql.JSON, nullable=True),
        sa.Column("children_snapshot", postgresql.JSON, nullable=True),
        sa.Column("fork_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("rating_sum", sa.Float, nullable=False, server_default=sa.text("0")),
        sa.Column("rating_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'published'")),
        sa.Column("region_name", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    # Geometry columns via raw SQL (PostGIS)
    op.execute("ALTER TABLE block_templates ADD COLUMN location_geom GEOMETRY(Point,4326)")

    # --- itinerary_blocks ---
    op.create_table(
        "itinerary_blocks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("itinerary_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("itineraries.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("parent_block_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("itinerary_blocks.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("day_index", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("block_type", sa.String(32), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("duration_minutes", sa.Integer, nullable=True),
        sa.Column("cost", sa.Numeric(10, 2), nullable=True),
        sa.Column("tips", sa.Text, nullable=True),
        sa.Column("address", sa.String(255), nullable=True),
        sa.Column("photos", postgresql.JSON, nullable=True),
        sa.Column("type_data", postgresql.JSON, nullable=True),
        sa.Column("is_container", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("source_template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("block_templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.execute("ALTER TABLE itinerary_blocks ADD COLUMN location_geom GEOMETRY(Point,4326)")

    # --- block_template_ratings ---
    op.create_table(
        "block_template_ratings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("block_templates.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("score", sa.Integer, nullable=False),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_unique_constraint("uq_template_user_rating", "block_template_ratings", ["template_id", "user_id"])


def downgrade() -> None:
    op.drop_table("block_template_ratings")
    op.drop_table("itinerary_blocks")
    op.drop_table("block_templates")
