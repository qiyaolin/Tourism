import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PoiTicketRule(Base):
    __tablename__ = "poi_ticket_rules"
    __table_args__ = (
        UniqueConstraint(
            "poi_id",
            "audience_code",
            "ticket_type",
            "time_slot",
            "is_active",
            name="uq_poi_ticket_rules_scope",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    poi_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pois.id", ondelete="CASCADE"), nullable=False, index=True
    )
    audience_code: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("pricing_audiences.code", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    ticket_type: Mapped[str] = mapped_column(String(64), nullable=False)
    time_slot: Mapped[str] = mapped_column(String(64), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="CNY")
    conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
