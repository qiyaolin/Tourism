import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from PIL import ExifTags, Image
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.bounty import BountySubmission, BountyTask
from app.models.poi import Poi
from app.models.territory import TerritoryRegion
from app.models.user import User
from app.schemas.bounty import (
    BountySubmissionItem,
    BountySubmissionListResponse,
    BountySubmitResponse,
    BountyTaskItem,
    BountyTaskListResponse,
)
from app.services.passport_service import evaluate_badges, record_contribution
from app.services.poi_correction_service import strip_exif_bytes
from app.services.storage import get_storage_provider
from app.services.territory_service import record_territory_contribution

logger = logging.getLogger(__name__)
settings = get_settings()

_ALLOWED_IMAGE_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
_GPS_INFO_TAG = next((k for k, v in ExifTags.TAGS.items() if v == "GPSInfo"), 34853)
_EXIF_TIME_TAGS = (36867, 36868, 306)


def _to_float(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _parse_point_text(raw: str) -> tuple[float, float]:
    cleaned = raw.strip()
    if cleaned.startswith("POINT(") and cleaned.endswith(")"):
        cleaned = cleaned[len("POINT(") : -1]
    lon_str, lat_str = cleaned.split(" ", maxsplit=1)
    return float(lon_str), float(lat_str)


def _haversine_distance_meters(
    longitude_a: float, latitude_a: float, longitude_b: float, latitude_b: float
) -> float:
    from math import asin, cos, radians, sin, sqrt

    earth_radius = 6371000.0
    dlon = radians(longitude_b - longitude_a)
    dlat = radians(latitude_b - latitude_a)
    lat1 = radians(latitude_a)
    lat2 = radians(latitude_b)
    value = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(value))
    return earth_radius * c


def _validate_image_upload(photo: UploadFile) -> tuple[str, str]:
    content_type = (photo.content_type or "").strip().lower()
    extension = _ALLOWED_IMAGE_TYPES.get(content_type)
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG/PNG/WEBP images are supported",
        )
    return content_type, extension


def _gps_part_to_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if hasattr(value, "numerator") and hasattr(value, "denominator"):
        denominator = getattr(value, "denominator", 0) or 0
        if denominator == 0:
            return None
        return float(getattr(value, "numerator", 0) / denominator)
    return None


def _gps_coord_to_decimal(ref: object, values: object) -> float | None:
    if not isinstance(values, (tuple, list)) or len(values) != 3:
        return None
    degrees = _gps_part_to_float(values[0])
    minutes = _gps_part_to_float(values[1])
    seconds = _gps_part_to_float(values[2])
    if degrees is None or minutes is None or seconds is None:
        return None
    decimal = degrees + minutes / 60 + seconds / 3600
    ref_text = str(ref or "").upper()
    if ref_text in {"S", "W"}:
        decimal *= -1
    return decimal


def _extract_exif_metadata(raw_bytes: bytes) -> tuple[datetime | None, float | None, float | None]:
    try:
        with Image.open(BytesIO(raw_bytes)) as image:
            exif = image.getexif()
    except Exception:
        return None, None, None
    if not exif:
        return None, None, None

    captured_at: datetime | None = None
    for key in _EXIF_TIME_TAGS:
        value = exif.get(key)
        if isinstance(value, str):
            try:
                parsed = datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
            except ValueError:
                continue
            captured_at = parsed.replace(tzinfo=UTC)
            break

    gps_info = exif.get(_GPS_INFO_TAG)
    if not isinstance(gps_info, dict):
        return captured_at, None, None

    gps_lat = _gps_coord_to_decimal(gps_info.get(1), gps_info.get(2))
    gps_lon = _gps_coord_to_decimal(gps_info.get(3), gps_info.get(4))
    return captured_at, gps_lon, gps_lat


def _resolve_poi_coordinate(db: Session, poi_id: UUID) -> tuple[float, float]:
    point_text = db.scalar(select(func.ST_AsText(Poi.geom)).where(Poi.id == poi_id).limit(1))
    if not point_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="POI coordinate is unavailable")
    return _parse_point_text(point_text)


def _normalize_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _validate_submission_coordinate(longitude: float, latitude: float) -> None:
    if not (-180 <= longitude <= 180) or not (-90 <= latitude <= 90):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid submission coordinates")


def _assert_new_user_cooldown(db: Session, current_user: User) -> None:
    if not settings.bounty_new_user_cooldown_enabled:
        return
    created_at = _normalize_utc(getattr(current_user, "created_at", None))
    if created_at is None:
        return
    now = datetime.now(UTC)
    if now - created_at > timedelta(days=settings.bounty_new_user_cooldown_days):
        return
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = db.scalar(
        select(func.count())
        .select_from(BountySubmission)
        .where(BountySubmission.submitter_user_id == current_user.id, BountySubmission.created_at >= day_start)
    ) or 0
    if today_count >= settings.bounty_new_user_daily_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="New user daily bounty submission limit exceeded",
        )


def _evaluate_risk(
    *,
    submit_longitude: float,
    submit_latitude: float,
    exif_captured_at: datetime | None,
    exif_longitude: float | None,
    exif_latitude: float | None,
    today_count: int,
) -> tuple[str, list[str]]:
    now = datetime.now(UTC)
    reasons: list[str] = []
    if today_count >= settings.bounty_high_freq_daily_limit:
        reasons.append("high_frequency")
    if exif_captured_at is None:
        reasons.append("missing_exif_time")
    else:
        if exif_captured_at > now + timedelta(hours=1):
            reasons.append("exif_future_time")
        if now - exif_captured_at > timedelta(days=7):
            reasons.append("exif_too_old")
    if exif_longitude is None or exif_latitude is None:
        reasons.append("missing_exif_location")
    else:
        exif_distance = _haversine_distance_meters(
            submit_longitude, submit_latitude, exif_longitude, exif_latitude
        )
        if exif_distance > float(settings.bounty_gps_radius_meters):
            reasons.append("exif_mismatch")
    if reasons:
        return "manual_review", reasons
    return "normal", []


def _build_task_item(
    task: BountyTask,
    *,
    poi_name: str,
    territory_name: str | None,
    distance_meters: float | None = None,
) -> BountyTaskItem:
    return BountyTaskItem(
        id=task.id,
        poi_id=task.poi_id,
        poi_name=poi_name,
        territory_id=task.territory_id,
        territory_name=territory_name,
        status=task.status,
        reward_points=task.reward_points,
        stale_days_snapshot=task.stale_days_snapshot,
        distance_meters=round(distance_meters, 2) if distance_meters is not None else None,
        generated_at=task.generated_at,
        expires_at=task.expires_at,
        claimed_by_user_id=task.claimed_by_user_id,
        claimed_at=task.claimed_at,
    )


def _build_submission_item(
    submission: BountySubmission,
    *,
    task_status: str,
    poi_name: str,
    territory_name: str | None,
    reward_points: int,
) -> BountySubmissionItem:
    return BountySubmissionItem(
        id=submission.id,
        task_id=submission.task_id,
        submitter_user_id=submission.submitter_user_id,
        submit_longitude=float(submission.submit_longitude),
        submit_latitude=float(submission.submit_latitude),
        distance_meters=float(submission.distance_meters),
        gps_verified=submission.gps_verified,
        photo_url=submission.photo_url,
        photo_exif_captured_at=submission.photo_exif_captured_at,
        photo_exif_longitude=_to_float(submission.photo_exif_longitude),
        photo_exif_latitude=_to_float(submission.photo_exif_latitude),
        risk_level=submission.risk_level,
        review_status=submission.review_status,
        reviewer_user_id=submission.reviewer_user_id,
        review_comment=submission.review_comment,
        reviewed_at=submission.reviewed_at,
        created_at=submission.created_at,
        task_status=task_status,
        poi_name=poi_name,
        territory_name=territory_name,
        reward_points=reward_points,
    )


def _load_task_with_names(db: Session, task_id: UUID) -> tuple[BountyTask, str, str | None]:
    row = db.execute(
        select(BountyTask, Poi.name, TerritoryRegion.name)
        .join(Poi, Poi.id == BountyTask.poi_id)
        .outerjoin(TerritoryRegion, TerritoryRegion.id == BountyTask.territory_id)
        .where(BountyTask.id == task_id)
        .limit(1)
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bounty task not found")
    task, poi_name, territory_name = row
    return task, poi_name, territory_name


def ensure_stale_bounty_tasks(db: Session) -> int:
    stale_days = max(int(settings.bounty_stale_days), 1)
    cutoff = datetime.now(UTC) - timedelta(days=stale_days)
    stale_rows = db.execute(
        select(Poi.id, Poi.territory_id)
        .where(func.coalesce(Poi.updated_at, Poi.created_at) < cutoff)
    ).all()
    if not stale_rows:
        return 0

    stale_poi_ids = [row[0] for row in stale_rows]
    existing_open_poi_ids = set(
        db.scalars(
            select(BountyTask.poi_id).where(
                BountyTask.poi_id.in_(stale_poi_ids),
                BountyTask.status.in_(("open", "claimed", "submitted")),
            )
        ).all()
    )

    generated_count = 0
    for poi_id, territory_id in stale_rows:
        if poi_id in existing_open_poi_ids:
            continue
        db.add(
            BountyTask(
                poi_id=poi_id,
                territory_id=territory_id,
                status="open",
                reward_points=settings.bounty_default_reward_points,
                stale_days_snapshot=stale_days,
                generated_at=datetime.now(UTC),
            )
        )
        generated_count += 1

    if generated_count > 0:
        db.commit()
    return generated_count


def list_bounty_tasks(
    db: Session,
    current_user: User,
    *,
    scope: str,
    offset: int,
    limit: int,
    longitude: float | None,
    latitude: float | None,
) -> BountyTaskListResponse:
    ensure_stale_bounty_tasks(db)
    rows = db.execute(
        select(BountyTask, Poi.name, TerritoryRegion.name)
        .join(Poi, Poi.id == BountyTask.poi_id)
        .outerjoin(TerritoryRegion, TerritoryRegion.id == BountyTask.territory_id)
        .where(BountyTask.status.in_(("open", "claimed", "submitted", "approved", "rejected")))
        .order_by(BountyTask.generated_at.desc())
    ).all()

    filtered: list[tuple[BountyTask, str, str | None, float | None]] = []
    if scope == "mine":
        for task, poi_name, territory_name in rows:
            if task.claimed_by_user_id == current_user.id:
                filtered.append((task, poi_name, territory_name, None))
    elif scope == "nearby":
        if longitude is None or latitude is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="longitude and latitude are required for nearby scope",
            )
        _validate_submission_coordinate(longitude, latitude)
        for task, poi_name, territory_name in rows:
            if task.status != "open":
                continue
            poi_lon, poi_lat = _resolve_poi_coordinate(db, task.poi_id)
            distance = _haversine_distance_meters(longitude, latitude, poi_lon, poi_lat)
            if distance <= settings.bounty_nearby_radius_meters:
                filtered.append((task, poi_name, territory_name, distance))
    else:
        for task, poi_name, territory_name in rows:
            if task.status == "open":
                filtered.append((task, poi_name, territory_name, None))

    total = len(filtered)
    paged = filtered[offset : offset + limit]
    items = [
        _build_task_item(task, poi_name=poi_name, territory_name=territory_name, distance_meters=distance)
        for task, poi_name, territory_name, distance in paged
    ]
    return BountyTaskListResponse(
        items=items,
        total=total,
        offset=offset,
        limit=limit,
        nearby_radius_meters=settings.bounty_nearby_radius_meters if scope == "nearby" else None,
    )


def claim_bounty_task(db: Session, task_id: UUID, current_user: User) -> BountyTaskItem:
    task = db.scalars(select(BountyTask).where(BountyTask.id == task_id).with_for_update()).first()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bounty task not found")
    if task.status == "claimed" and task.claimed_by_user_id == current_user.id:
        task_row, poi_name, territory_name = _load_task_with_names(db, task.id)
        return _build_task_item(task_row, poi_name=poi_name, territory_name=territory_name)
    if task.status != "open":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bounty task is not claimable")

    now = datetime.now(UTC)
    task.status = "claimed"
    task.claimed_by_user_id = current_user.id
    task.claimed_at = now
    db.add(task)
    db.commit()
    db.refresh(task)

    task_row, poi_name, territory_name = _load_task_with_names(db, task.id)
    return _build_task_item(task_row, poi_name=poi_name, territory_name=territory_name)


def _approve_submission(
    db: Session,
    *,
    task: BountyTask,
    submission: BountySubmission,
    reviewer_user_id: UUID | None,
    review_comment: str | None,
) -> None:
    now = datetime.now(UTC)
    submission.review_status = "approved"
    submission.reviewer_user_id = reviewer_user_id
    submission.review_comment = review_comment
    submission.reviewed_at = now
    db.add(submission)

    task.status = "approved"
    task.approved_at = now
    task.approved_by_user_id = reviewer_user_id
    db.add(task)

    try:
        record_contribution(
            session=db,
            user_id=submission.submitter_user_id,
            action_type="bounty_completed",
            points=task.reward_points,
            source_id=submission.id,
        )
        evaluate_badges(db, submission.submitter_user_id)
        if task.territory_id is not None:
            record_territory_contribution(
                db=db,
                user_id=submission.submitter_user_id,
                territory_id=task.territory_id,
                action_type="verification",
            )
    except Exception as exc:
        logger.error("Failed to record bounty contribution for %s: %s", submission.id, exc)


async def submit_bounty_task(
    db: Session,
    *,
    task_id: UUID,
    current_user: User,
    submit_longitude: float,
    submit_latitude: float,
    details: str | None,
    photo: UploadFile,
) -> BountySubmitResponse:
    _assert_new_user_cooldown(db, current_user)
    _validate_submission_coordinate(submit_longitude, submit_latitude)

    task = db.scalars(select(BountyTask).where(BountyTask.id == task_id).with_for_update()).first()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bounty task not found")
    if task.claimed_by_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Task must be claimed by current user")
    if task.status != "claimed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task is not in claim state")

    if photo is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Photo is required")
    content_type, extension = _validate_image_upload(photo)
    raw_photo = await photo.read()
    if not raw_photo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Photo file is empty")

    exif_captured_at, exif_longitude, exif_latitude = _extract_exif_metadata(raw_photo)

    poi_longitude, poi_latitude = _resolve_poi_coordinate(db, task.poi_id)
    distance_meters = _haversine_distance_meters(
        submit_longitude, submit_latitude, poi_longitude, poi_latitude
    )
    if distance_meters > settings.bounty_gps_radius_meters:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="GPS verification failed: too far from target POI",
        )

    cleaned_photo = strip_exif_bytes(raw_photo, extension)
    storage = get_storage_provider()
    photo_storage_key, photo_url = storage.save_bytes(
        content=cleaned_photo,
        extension=extension,
        content_type=content_type,
    )

    day_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    today_submission_count = db.scalar(
        select(func.count())
        .select_from(BountySubmission)
        .where(BountySubmission.submitter_user_id == current_user.id, BountySubmission.created_at >= day_start)
    ) or 0
    risk_level, risk_reasons = _evaluate_risk(
        submit_longitude=submit_longitude,
        submit_latitude=submit_latitude,
        exif_captured_at=exif_captured_at,
        exif_longitude=exif_longitude,
        exif_latitude=exif_latitude,
        today_count=today_submission_count,
    )

    now = datetime.now(UTC)
    submission = BountySubmission(
        task_id=task.id,
        submitter_user_id=current_user.id,
        submit_longitude=submit_longitude,
        submit_latitude=submit_latitude,
        distance_meters=distance_meters,
        gps_verified=True,
        photo_url=photo_url,
        photo_storage_key=photo_storage_key,
        photo_exif_captured_at=exif_captured_at,
        photo_exif_longitude=exif_longitude,
        photo_exif_latitude=exif_latitude,
        payload_json={"details": details.strip() if details else None, "risk_reasons": risk_reasons},
        risk_level=risk_level,
        review_status="pending",
    )
    db.add(submission)
    db.flush()

    task.status = "submitted"
    task.completed_at = now
    db.add(task)

    auto_approved = False
    if risk_level == "normal":
        auto_approved = True
        _approve_submission(
            db=db,
            task=task,
            submission=submission,
            reviewer_user_id=None,
            review_comment="系统自动通过：GPS 与 EXIF 校验通过",
        )

    db.commit()
    db.refresh(submission)
    db.refresh(task)
    task_row, poi_name, territory_name = _load_task_with_names(db, task.id)
    return BountySubmitResponse(
        task=_build_task_item(task_row, poi_name=poi_name, territory_name=territory_name),
        submission=_build_submission_item(
            submission,
            task_status=task.status,
            poi_name=poi_name,
            territory_name=territory_name,
            reward_points=task.reward_points,
        ),
        auto_approved=auto_approved,
    )


def list_my_bounty_submissions(
    db: Session, current_user: User, *, offset: int, limit: int
) -> BountySubmissionListResponse:
    base_stmt = (
        select(BountySubmission, BountyTask.status, BountyTask.reward_points, Poi.name, TerritoryRegion.name)
        .join(BountyTask, BountyTask.id == BountySubmission.task_id)
        .join(Poi, Poi.id == BountyTask.poi_id)
        .outerjoin(TerritoryRegion, TerritoryRegion.id == BountyTask.territory_id)
        .where(BountySubmission.submitter_user_id == current_user.id)
    )
    total = db.scalar(select(func.count()).select_from(base_stmt.subquery())) or 0
    rows = db.execute(base_stmt.order_by(BountySubmission.created_at.desc()).offset(offset).limit(limit)).all()
    items = [
        _build_submission_item(
            submission,
            task_status=task_status,
            poi_name=poi_name,
            territory_name=territory_name,
            reward_points=reward_points,
        )
        for submission, task_status, reward_points, poi_name, territory_name in rows
    ]
    return BountySubmissionListResponse(items=items, total=total, offset=offset, limit=limit)


def list_admin_bounty_submissions(
    db: Session, *, review_status_filter: str, offset: int, limit: int
) -> BountySubmissionListResponse:
    base_stmt = (
        select(BountySubmission, BountyTask.status, BountyTask.reward_points, Poi.name, TerritoryRegion.name)
        .join(BountyTask, BountyTask.id == BountySubmission.task_id)
        .join(Poi, Poi.id == BountyTask.poi_id)
        .outerjoin(TerritoryRegion, TerritoryRegion.id == BountyTask.territory_id)
    )
    if review_status_filter != "all":
        base_stmt = base_stmt.where(BountySubmission.review_status == review_status_filter)
    total = db.scalar(select(func.count()).select_from(base_stmt.subquery())) or 0
    rows = db.execute(base_stmt.order_by(BountySubmission.created_at.desc()).offset(offset).limit(limit)).all()
    items = [
        _build_submission_item(
            submission,
            task_status=task_status,
            poi_name=poi_name,
            territory_name=territory_name,
            reward_points=reward_points,
        )
        for submission, task_status, reward_points, poi_name, territory_name in rows
    ]
    return BountySubmissionListResponse(items=items, total=total, offset=offset, limit=limit)


def review_bounty_submission(
    db: Session,
    *,
    submission_id: UUID,
    action: str,
    review_comment: str | None,
    current_user: User,
) -> BountySubmissionItem:
    submission = db.scalars(
        select(BountySubmission).where(BountySubmission.id == submission_id).with_for_update()
    ).first()
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bounty submission not found")
    if submission.review_status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Submission already reviewed")

    task = db.get(BountyTask, submission.task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bounty task not found")

    now = datetime.now(UTC)
    if action == "approve":
        _approve_submission(
            db=db,
            task=task,
            submission=submission,
            reviewer_user_id=current_user.id,
            review_comment=review_comment.strip() if review_comment else None,
        )
    else:
        submission.review_status = "rejected"
        submission.reviewer_user_id = current_user.id
        submission.review_comment = review_comment.strip() if review_comment else None
        submission.reviewed_at = now
        db.add(submission)

        task.status = "rejected"
        task.reject_reason = review_comment.strip() if review_comment else "Manual review rejected"
        task.approved_at = None
        task.approved_by_user_id = None
        db.add(task)

    db.commit()
    db.refresh(submission)
    db.refresh(task)

    _, poi_name, territory_name = _load_task_with_names(db, task.id)
    return _build_submission_item(
        submission,
        task_status=task.status,
        poi_name=poi_name,
        territory_name=territory_name,
        reward_points=task.reward_points,
    )
