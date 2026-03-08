"""editor board v3 schema

Revision ID: 20260226_0019
Revises: 20260225_0018
Create Date: 2026-02-26
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260226_0019"
down_revision = "20260225_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "itinerary_blocks",
        sa.Column("lane_key", sa.String(length=32), nullable=False, server_default=sa.text("'core'")),
    )
    op.add_column(
        "itinerary_blocks",
        sa.Column("start_minute", sa.Integer(), nullable=True),
    )
    op.add_column(
        "itinerary_blocks",
        sa.Column("end_minute", sa.Integer(), nullable=True),
    )
    op.add_column(
        "itinerary_blocks",
        sa.Column("status", sa.String(length=16), nullable=False, server_default=sa.text("'draft'")),
    )
    op.add_column(
        "itinerary_blocks",
        sa.Column("priority", sa.String(length=16), nullable=False, server_default=sa.text("'medium'")),
    )
    op.add_column(
        "itinerary_blocks",
        sa.Column("risk_level", sa.String(length=16), nullable=False, server_default=sa.text("'low'")),
    )
    op.add_column(
        "itinerary_blocks",
        sa.Column("assignee_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "itinerary_blocks",
        sa.Column("tags", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "itinerary_blocks",
        sa.Column("ui_meta", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
    op.create_foreign_key(
        "fk_itinerary_blocks_assignee_user_id_users",
        "itinerary_blocks",
        "users",
        ["assignee_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_itinerary_blocks_assignee_user_id", "itinerary_blocks", ["assignee_user_id"], unique=False)

    op.create_table(
        "itinerary_block_edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("itinerary_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_block_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_block_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("edge_type", sa.String(length=16), nullable=False, server_default=sa.text("'hard'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["from_block_id"], ["itinerary_blocks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["itinerary_id"], ["itineraries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_block_id"], ["itinerary_blocks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("itinerary_id", "from_block_id", "to_block_id", name="uq_block_edge_unique"),
    )
    op.create_index(
        "ix_itinerary_block_edges_itinerary_id",
        "itinerary_block_edges",
        ["itinerary_id"],
        unique=False,
    )
    op.create_index(
        "ix_itinerary_block_edges_from_block_id",
        "itinerary_block_edges",
        ["from_block_id"],
        unique=False,
    )
    op.create_index(
        "ix_itinerary_block_edges_to_block_id",
        "itinerary_block_edges",
        ["to_block_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_itinerary_block_edges_to_block_id", table_name="itinerary_block_edges")
    op.drop_index("ix_itinerary_block_edges_from_block_id", table_name="itinerary_block_edges")
    op.drop_index("ix_itinerary_block_edges_itinerary_id", table_name="itinerary_block_edges")
    op.drop_table("itinerary_block_edges")

    op.drop_index("ix_itinerary_blocks_assignee_user_id", table_name="itinerary_blocks")
    op.drop_constraint("fk_itinerary_blocks_assignee_user_id_users", "itinerary_blocks", type_="foreignkey")
    op.drop_column("itinerary_blocks", "ui_meta")
    op.drop_column("itinerary_blocks", "tags")
    op.drop_column("itinerary_blocks", "assignee_user_id")
    op.drop_column("itinerary_blocks", "risk_level")
    op.drop_column("itinerary_blocks", "priority")
    op.drop_column("itinerary_blocks", "status")
    op.drop_column("itinerary_blocks", "end_minute")
    op.drop_column("itinerary_blocks", "start_minute")
    op.drop_column("itinerary_blocks", "lane_key")
