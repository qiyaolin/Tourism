"""professionalize correction type labels and input metadata

Revision ID: 20260220_0009
Revises: 20260219_0008
Create Date: 2026-02-20 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260220_0009"
down_revision: str | None = "20260219_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "poi_correction_types",
        sa.Column("input_mode", sa.String(length=32), nullable=False, server_default="text"),
    )
    op.add_column(
        "poi_correction_types",
        sa.Column("input_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "poi_correction_types",
        sa.Column("help_text", sa.String(length=255), nullable=True),
    )

    op.execute(
        """
        UPDATE poi_correction_types
        SET
            label = CASE
                WHEN code = 'ticket_price_changed' THEN '票价变动'
                WHEN code = 'opening_hours_changed' THEN '营业时间调整'
                WHEN code = 'address_changed' THEN '地址纠偏'
                WHEN code = 'temporary_closed' THEN '临时闭园通知'
                WHEN code = 'other' THEN '其他信息纠错'
                ELSE label
            END,
            placeholder = CASE
                WHEN code = 'ticket_price_changed' THEN '请按规则填写票价变动'
                WHEN code = 'opening_hours_changed' THEN '例如：09:00-18:00'
                WHEN code = 'address_changed' THEN '请填写标准、可导航的地址'
                WHEN code = 'temporary_closed' THEN '例如：临时闭园至 2026-03-01'
                WHEN code = 'other' THEN '请描述具体问题与更正建议'
                ELSE placeholder
            END,
            value_kind = CASE
                WHEN code = 'ticket_price_changed' THEN 'string'
                ELSE value_kind
            END,
            input_mode = CASE
                WHEN code = 'ticket_price_changed' THEN 'ticket_rules'
                WHEN code = 'opening_hours_changed' THEN 'time_range'
                ELSE 'text'
            END,
            input_schema = CASE
                WHEN code = 'ticket_price_changed' THEN
                    '{"columns":["audience_code","ticket_type","time_slot","conditions","price"],"currency":"CNY"}'::jsonb
                WHEN code = 'opening_hours_changed' THEN
                    '{"format":"HH:MM-HH:MM","timezone":"local"}'::jsonb
                ELSE NULL
            END,
            help_text = CASE
                WHEN code = 'ticket_price_changed' THEN '按人群逐条填写票种、适用时段、使用条件和票价，审核通过后可直接应用。'
                WHEN code = 'opening_hours_changed' THEN '请使用 24 小时制时间段（如 09:00-18:00）。'
                WHEN code = 'address_changed' THEN '请提供完整地址或可定位描述，便于审核后直接覆盖。'
                WHEN code = 'temporary_closed' THEN '请写明闭园原因与预计恢复时间。'
                WHEN code = 'other' THEN '用于无法归类的问题，建议附补充说明和图片证据。'
                ELSE help_text
            END
        WHERE code IN (
            'ticket_price_changed',
            'opening_hours_changed',
            'address_changed',
            'temporary_closed',
            'other'
        )
        """
    )

    op.alter_column("poi_correction_types", "input_mode", server_default=None)


def downgrade() -> None:
    op.execute(
        """
        UPDATE poi_correction_types
        SET
            label = CASE
                WHEN code = 'ticket_price_changed' THEN '价格变了'
                WHEN code = 'opening_hours_changed' THEN '营业时间变了'
                WHEN code = 'address_changed' THEN '位置有误'
                WHEN code = 'temporary_closed' THEN '关门了'
                WHEN code = 'other' THEN '其他'
                ELSE label
            END,
            placeholder = CASE
                WHEN code = 'ticket_price_changed' THEN '例如：85'
                WHEN code = 'opening_hours_changed' THEN '例如：09:00-18:00'
                WHEN code = 'address_changed' THEN '请填写更准确的地址'
                WHEN code = 'temporary_closed' THEN '例如：临时停业至 2026-03-01'
                WHEN code = 'other' THEN '请描述你发现的问题'
                ELSE placeholder
            END,
            value_kind = CASE
                WHEN code = 'ticket_price_changed' THEN 'number'
                ELSE value_kind
            END
        WHERE code IN (
            'ticket_price_changed',
            'opening_hours_changed',
            'address_changed',
            'temporary_closed',
            'other'
        )
        """
    )

    op.drop_column("poi_correction_types", "help_text")
    op.drop_column("poi_correction_types", "input_schema")
    op.drop_column("poi_correction_types", "input_mode")
