"""create itinerary collab tables

Revision ID: 20260220_0012
Revises: 20260220_0011
Create Date: 2026-02-20 19:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260220_0012"
down_revision: str | None = "20260220_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "itinerary_collab_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("itinerary_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("permission", sa.String(length=16), nullable=False, server_default="edit"),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "permission IN ('edit', 'read')",
            name="ck_itinerary_collab_links_permission",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["itinerary_id"], ["itineraries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_itinerary_collab_links_itinerary_id"), "itinerary_collab_links", ["itinerary_id"]
    )
    op.create_index(
        op.f("ix_itinerary_collab_links_token_hash"), "itinerary_collab_links", ["token_hash"]
    )
    op.create_unique_constraint(
        "uq_itinerary_collab_links_token_hash", "itinerary_collab_links", ["token_hash"]
    )

    op.create_table(
        "itinerary_collab_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("itinerary_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("link_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("participant_type", sa.String(length=16), nullable=False),
        sa.Column("participant_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("guest_name", sa.String(length=64), nullable=True),
        sa.Column("permission", sa.String(length=16), nullable=False, server_default="read"),
        sa.Column("connection_id", sa.String(length=64), nullable=False),
        sa.Column(
            "joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "participant_type IN ('user', 'guest')",
            name="ck_itinerary_collab_sessions_participant_type",
        ),
        sa.ForeignKeyConstraint(["itinerary_id"], ["itineraries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["link_id"], ["itinerary_collab_links.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["participant_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_itinerary_collab_sessions_itinerary_id"),
        "itinerary_collab_sessions",
        ["itinerary_id"],
    )
    op.create_index(
        op.f("ix_itinerary_collab_sessions_link_id"), "itinerary_collab_sessions", ["link_id"]
    )
    op.create_index(
        op.f("ix_itinerary_collab_sessions_participant_user_id"),
        "itinerary_collab_sessions",
        ["participant_user_id"],
    )
    op.create_index(
        op.f("ix_itinerary_collab_sessions_connection_id"),
        "itinerary_collab_sessions",
        ["connection_id"],
    )

    op.create_table(
        "itinerary_collab_documents",
        sa.Column("itinerary_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state_update", sa.LargeBinary(), nullable=True),
        sa.Column("update_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["itinerary_id"], ["itineraries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("itinerary_id"),
    )

    op.create_table(
        "itinerary_collab_event_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("itinerary_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_type", sa.String(length=16), nullable=False, server_default="system"),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("guest_name", sa.String(length=64), nullable=True),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=True),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "actor_type IN ('system', 'user', 'guest')",
            name="ck_itinerary_collab_event_logs_actor_type",
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["itinerary_id"], ["itineraries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_itinerary_collab_event_logs_itinerary_id"),
        "itinerary_collab_event_logs",
        ["itinerary_id"],
    )
    op.create_index(
        op.f("ix_itinerary_collab_event_logs_actor_user_id"),
        "itinerary_collab_event_logs",
        ["actor_user_id"],
    )
    op.create_index(
        op.f("ix_itinerary_collab_event_logs_event_type"),
        "itinerary_collab_event_logs",
        ["event_type"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_itinerary_collab_event_logs_event_type"), table_name="itinerary_collab_event_logs"
    )
    op.drop_index(
        op.f("ix_itinerary_collab_event_logs_actor_user_id"),
        table_name="itinerary_collab_event_logs",
    )
    op.drop_index(
        op.f("ix_itinerary_collab_event_logs_itinerary_id"),
        table_name="itinerary_collab_event_logs",
    )
    op.drop_table("itinerary_collab_event_logs")

    op.drop_table("itinerary_collab_documents")

    op.drop_index(
        op.f("ix_itinerary_collab_sessions_connection_id"), table_name="itinerary_collab_sessions"
    )
    op.drop_index(
        op.f("ix_itinerary_collab_sessions_participant_user_id"),
        table_name="itinerary_collab_sessions",
    )
    op.drop_index(
        op.f("ix_itinerary_collab_sessions_link_id"), table_name="itinerary_collab_sessions"
    )
    op.drop_index(
        op.f("ix_itinerary_collab_sessions_itinerary_id"), table_name="itinerary_collab_sessions"
    )
    op.drop_table("itinerary_collab_sessions")

    op.drop_constraint(
        "uq_itinerary_collab_links_token_hash", "itinerary_collab_links", type_="unique"
    )
    op.drop_index(op.f("ix_itinerary_collab_links_token_hash"), table_name="itinerary_collab_links")
    op.drop_index(
        op.f("ix_itinerary_collab_links_itinerary_id"), table_name="itinerary_collab_links"
    )
    op.drop_table("itinerary_collab_links")
