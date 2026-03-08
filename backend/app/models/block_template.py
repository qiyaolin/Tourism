import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import GeometryPoint


class BlockTemplate(Base):
    __tablename__ = "block_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    style_tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # ["tag1", "tag2"]
    block_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # "scenic"|"dining"|...|"group" (group = composition template)
    is_group: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Template content: JSON snapshot of block fields
    content_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Children snapshot for group templates
    children_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Community metrics
    fork_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rating_sum: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rating_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="published")
    # published | draft | hidden

    # Location for regional search
    location_geom: Mapped[str | None] = mapped_column(GeometryPoint(), nullable=True)
    region_name: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class BlockTemplateRating(Base):
    __tablename__ = "block_template_ratings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("block_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
