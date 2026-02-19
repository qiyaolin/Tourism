"""create itinerary fork and snapshot tables

Revision ID: 20260218_0004
Revises: 20260218_0003
Create Date: 2026-02-18 16:20:00
"""

import json
from collections.abc import Sequence
from datetime import datetime
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260218_0004"
down_revision: str | None = "20260218_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _parse_point_text(value: str) -> tuple[float, float]:
    raw = value.strip().removeprefix("POINT(").removesuffix(")")
    lon_str, lat_str = raw.split(" ", maxsplit=1)
    return float(lon_str), float(lat_str)


def _backfill_snapshots() -> None:
    bind = op.get_bind()
    itinerary_rows = bind.execute(
        text(
            """
            SELECT id, title, destination, days, status, visibility, cover_image_url
            FROM itineraries
            WHERE status = 'published'
            """
        )
    ).mappings().all()

    for itinerary in itinerary_rows:
        item_rows = bind.execute(
            text(
                """
                SELECT
                    ii.day_index,
                    ii.sort_order,
                    ii.poi_id,
                    ii.start_time,
                    ii.duration_minutes,
                    ii.cost,
                    ii.tips,
                    p.name AS poi_name,
                    p.type AS poi_type,
                    p.address,
                    p.opening_hours,
                    p.ticket_price,
                    ST_AsText(p.geom) AS poi_wkt
                FROM itinerary_items AS ii
                JOIN pois AS p ON p.id = ii.poi_id
                WHERE ii.itinerary_id = :itinerary_id
                ORDER BY ii.day_index ASC, ii.sort_order ASC
                """
            ),
            {"itinerary_id": itinerary["id"]},
        ).mappings().all()

        items: list[dict[str, object]] = []
        for row in item_rows:
            longitude, latitude = _parse_point_text(row["poi_wkt"])
            items.append(
                {
                    "day_index": row["day_index"],
                    "sort_order": row["sort_order"],
                    "poi_id": str(row["poi_id"]),
                    "poi_name": row["poi_name"],
                    "poi_type": row["poi_type"],
                    "longitude": longitude,
                    "latitude": latitude,
                    "address": row["address"],
                    "opening_hours": row["opening_hours"],
                    "ticket_price": (
                        float(row["ticket_price"])
                        if row["ticket_price"] is not None
                        else None
                    ),
                    "start_time": (
                        row["start_time"].isoformat()
                        if row["start_time"] is not None
                        else None
                    ),
                    "duration_minutes": row["duration_minutes"],
                    "cost": float(row["cost"]) if row["cost"] is not None else None,
                    "tips": row["tips"],
                }
            )

        snapshot_json = {
            "meta": {
                "title": itinerary["title"],
                "destination": itinerary["destination"],
                "days": itinerary["days"],
                "status": itinerary["status"],
                "visibility": itinerary["visibility"],
                "cover_image_url": itinerary["cover_image_url"],
            },
            "items": items,
        }
        bind.execute(
            text(
                """
                INSERT INTO itinerary_snapshots (
                    id, itinerary_id, version_no, snapshot_json, created_at
                )
                VALUES (:id, :itinerary_id, :version_no, CAST(:snapshot_json AS JSONB), :created_at)
                """
            ),
            {
                "id": str(uuid4()),
                "itinerary_id": str(itinerary["id"]),
                "version_no": 1,
                "snapshot_json": json.dumps(snapshot_json, ensure_ascii=False),
                "created_at": datetime.utcnow(),
            },
        )


def upgrade() -> None:
    op.create_table(
        "itinerary_snapshots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("itinerary_id", sa.UUID(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column(
            "snapshot_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["itinerary_id"], ["itineraries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("itinerary_id", "version_no", name="uq_itinerary_snapshot_version"),
    )
    op.create_index(
        "ix_itinerary_snapshots_itinerary_id",
        "itinerary_snapshots",
        ["itinerary_id"],
        unique=False,
    )

    op.create_table(
        "itinerary_forks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_itinerary_id", sa.UUID(), nullable=False),
        sa.Column("forked_itinerary_id", sa.UUID(), nullable=False),
        sa.Column("forked_by_user_id", sa.UUID(), nullable=False),
        sa.Column("source_snapshot_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["forked_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["forked_itinerary_id"], ["itineraries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_itinerary_id"], ["itineraries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["source_snapshot_id"],
            ["itinerary_snapshots.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("forked_itinerary_id"),
    )
    op.create_index(
        "ix_itinerary_forks_source_itinerary_id",
        "itinerary_forks",
        ["source_itinerary_id"],
        unique=False,
    )
    op.create_index(
        "ix_itinerary_forks_forked_itinerary_id",
        "itinerary_forks",
        ["forked_itinerary_id"],
        unique=False,
    )
    op.create_index(
        "ix_itinerary_forks_forked_by_user_id",
        "itinerary_forks",
        ["forked_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_itinerary_forks_source_snapshot_id",
        "itinerary_forks",
        ["source_snapshot_id"],
        unique=False,
    )

    _backfill_snapshots()


def downgrade() -> None:
    op.drop_index("ix_itinerary_forks_source_snapshot_id", table_name="itinerary_forks")
    op.drop_index("ix_itinerary_forks_forked_by_user_id", table_name="itinerary_forks")
    op.drop_index("ix_itinerary_forks_forked_itinerary_id", table_name="itinerary_forks")
    op.drop_index("ix_itinerary_forks_source_itinerary_id", table_name="itinerary_forks")
    op.drop_table("itinerary_forks")

    op.drop_index("ix_itinerary_snapshots_itinerary_id", table_name="itinerary_snapshots")
    op.drop_table("itinerary_snapshots")
