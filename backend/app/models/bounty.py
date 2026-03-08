import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BountyTask(Base):
    __tablename__ = "bounty_tasks"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'claimed', 'submitted', 'approved', 'rejected', 'expired')",
            name="ck_bounty_tasks_status",
        ),
        CheckConstraint("reward_points >= 0", name="ck_bounty_tasks_reward_points_nonnegative"),
        CheckConstraint("stale_days_snapshot >= 0", name="ck_bounty_tasks_stale_days_nonnegative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    poi_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pois.id", ondelete="CASCADE"), nullable=False, index=True
    )
    territory_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("territory_regions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open", index=True)
    reward_points: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    stale_days_snapshot: Mapped[int] = mapped_column(Integer, nullable=False, default=45)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    claimed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class BountySubmission(Base):
    __tablename__ = "bounty_submissions"
    __table_args__ = (
        CheckConstraint("distance_meters >= 0", name="ck_bounty_submissions_distance_nonnegative"),
        CheckConstraint("submit_longitude BETWEEN -180 AND 180", name="ck_bounty_submissions_longitude_range"),
        CheckConstraint("submit_latitude BETWEEN -90 AND 90", name="ck_bounty_submissions_latitude_range"),
        CheckConstraint("review_status IN ('pending', 'approved', 'rejected')", name="ck_bounty_submissions_review_status"),
        CheckConstraint("risk_level IN ('normal', 'manual_review')", name="ck_bounty_submissions_risk_level"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bounty_tasks.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    submitter_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    submit_longitude: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    submit_latitude: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    distance_meters: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    gps_verified: Mapped[bool] = mapped_column(nullable=False, default=False)
    photo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    photo_storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    photo_exif_captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    photo_exif_longitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    photo_exif_latitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    review_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    reviewer_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
