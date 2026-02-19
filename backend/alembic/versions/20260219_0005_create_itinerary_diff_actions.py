"""create itinerary diff action table

Revision ID: 20260219_0005
Revises: 20260218_0004
Create Date: 2026-02-19 01:40:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260219_0005"
down_revision: str | None = "20260218_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "itinerary_diff_actions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("itinerary_id", sa.UUID(), nullable=False),
        sa.Column("source_snapshot_id", sa.UUID(), nullable=False),
        sa.Column("diff_key", sa.String(length=128), nullable=False),
        sa.Column("diff_type", sa.String(length=16), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("actor_user_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["itinerary_id"], ["itineraries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_snapshot_id"], ["itinerary_snapshots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_itinerary_diff_actions_itinerary_id",
        "itinerary_diff_actions",
        ["itinerary_id"],
        unique=False,
    )
    op.create_index(
        "ix_itinerary_diff_actions_source_snapshot_id",
        "itinerary_diff_actions",
        ["source_snapshot_id"],
        unique=False,
    )
    op.create_index(
        "ix_itinerary_diff_actions_diff_key",
        "itinerary_diff_actions",
        ["diff_key"],
        unique=False,
    )
    op.create_index(
        "ix_itinerary_diff_actions_diff_type",
        "itinerary_diff_actions",
        ["diff_type"],
        unique=False,
    )
    op.create_index(
        "ix_itinerary_diff_actions_action",
        "itinerary_diff_actions",
        ["action"],
        unique=False,
    )
    op.create_index(
        "ix_itinerary_diff_actions_actor_user_id",
        "itinerary_diff_actions",
        ["actor_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_itinerary_diff_actions_actor_user_id", table_name="itinerary_diff_actions")
    op.drop_index("ix_itinerary_diff_actions_action", table_name="itinerary_diff_actions")
    op.drop_index("ix_itinerary_diff_actions_diff_type", table_name="itinerary_diff_actions")
    op.drop_index("ix_itinerary_diff_actions_diff_key", table_name="itinerary_diff_actions")
    op.drop_index("ix_itinerary_diff_actions_source_snapshot_id", table_name="itinerary_diff_actions")
    op.drop_index("ix_itinerary_diff_actions_itinerary_id", table_name="itinerary_diff_actions")
    op.drop_table("itinerary_diff_actions")
