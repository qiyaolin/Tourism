"""add ticket rules and correction context

Revision ID: 20260219_0007
Revises: 20260219_0006
Create Date: 2026-02-19 14:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260219_0007"
down_revision: str | None = "20260219_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pricing_audiences",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("label", sa.String(length=32), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_pricing_audiences_code", "pricing_audiences", ["code"], unique=True)

    op.create_table(
        "poi_ticket_rules",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("poi_id", sa.UUID(), nullable=False),
        sa.Column("audience_code", sa.String(length=32), nullable=False),
        sa.Column("ticket_type", sa.String(length=64), nullable=False),
        sa.Column("time_slot", sa.String(length=64), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="CNY"),
        sa.Column("conditions", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=False, server_default="manual"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["poi_id"], ["pois.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["audience_code"], ["pricing_audiences.code"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "poi_id",
            "audience_code",
            "ticket_type",
            "time_slot",
            "is_active",
            name="uq_poi_ticket_rules_scope",
        ),
    )
    op.create_index("ix_poi_ticket_rules_poi_id", "poi_ticket_rules", ["poi_id"], unique=False)
    op.create_index(
        "ix_poi_ticket_rules_audience_code",
        "poi_ticket_rules",
        ["audience_code"],
        unique=False,
    )

    op.add_column(
        "poi_corrections",
        sa.Column("source_poi_name_snapshot", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "poi_corrections",
        sa.Column("source_itinerary_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "poi_corrections",
        sa.Column("source_itinerary_title_snapshot", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "poi_corrections",
        sa.Column("source_itinerary_author_snapshot", sa.String(length=64), nullable=True),
    )
    op.create_foreign_key(
        "fk_poi_corrections_source_itinerary_id",
        "poi_corrections",
        "itineraries",
        ["source_itinerary_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_poi_corrections_source_itinerary_id",
        "poi_corrections",
        ["source_itinerary_id"],
        unique=False,
    )

    op.execute(
        """
        INSERT INTO pricing_audiences (id, code, label, sort_order, is_active)
        VALUES
            ('6eac254e-102e-4f38-a353-9a03870f2730', 'adult', '成人', 10, true),
            ('ef89f7d4-c7d6-42f4-9e23-9f5c48392f9f', 'student', '学生', 20, true),
            ('8cb53ad5-3158-475d-bf10-7699ca89059f', 'senior', '老人', 30, true),
            ('f5dcb2ea-f68c-4924-84b7-a8f4638ef246', 'child', '儿童', 40, true),
            ('8c2b11c5-ac10-4f9f-a49d-e24985a5965e', 'soldier', '军人', 50, true),
            ('5f94f4a8-eb6b-45a0-b425-a6f7487b1747', 'disabled', '残疾人', 60, true)
        """
    )
    op.execute(
        """
        INSERT INTO poi_ticket_rules (id, poi_id, audience_code, ticket_type, time_slot, price, currency, conditions, source, is_active)
        SELECT
            md5(p.id::text || ':adult:标准票:全天')::uuid,
            p.id,
            'adult',
            '标准票',
            '全天',
            p.ticket_price,
            'CNY',
            NULL,
            'migration',
            true
        FROM pois p
        WHERE p.ticket_price IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_poi_corrections_source_itinerary_id", table_name="poi_corrections")
    op.drop_constraint("fk_poi_corrections_source_itinerary_id", "poi_corrections", type_="foreignkey")
    op.drop_column("poi_corrections", "source_itinerary_author_snapshot")
    op.drop_column("poi_corrections", "source_itinerary_title_snapshot")
    op.drop_column("poi_corrections", "source_itinerary_id")
    op.drop_column("poi_corrections", "source_poi_name_snapshot")

    op.drop_index("ix_poi_ticket_rules_audience_code", table_name="poi_ticket_rules")
    op.drop_index("ix_poi_ticket_rules_poi_id", table_name="poi_ticket_rules")
    op.drop_table("poi_ticket_rules")

    op.drop_index("ix_pricing_audiences_code", table_name="pricing_audiences")
    op.drop_table("pricing_audiences")
