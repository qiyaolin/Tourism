import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PoiCorrectionType(Base):
    __tablename__ = "poi_correction_types"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    target_field: Mapped[str] = mapped_column(String(64), nullable=False)
    value_kind: Mapped[str] = mapped_column(String(16), nullable=False, default="string")
    placeholder: Mapped[str | None] = mapped_column(String(255), nullable=True)
    input_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="text")
    input_schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    help_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
