import hashlib
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.itinerary import Itinerary
from app.models.itinerary_fork import ItineraryFork
from app.models.itinerary_item import ItineraryItem
from app.models.poi_correction import PoiCorrection
from app.models.user import User
from app.models.user_notification import UserNotification
from app.schemas.notification import (
    MarkAllNotificationsReadResponse,
    UserNotificationListResponse,
    UserNotificationResponse,
)


def _to_response(row: UserNotification) -> UserNotificationResponse:
    return UserNotificationResponse(
        id=row.id,
        recipient_user_id=row.recipient_user_id,
        sender_user_id=row.sender_user_id,
        event_type=row.event_type,
        severity=row.severity,
        title=row.title,
        content=row.content,
        is_read=row.is_read,
        read_at=row.read_at,
        source_itinerary_id=row.source_itinerary_id,
        forked_itinerary_id=row.forked_itinerary_id,
        source_snapshot_id=row.source_snapshot_id,
        correction_id=row.correction_id,
        poi_id=row.poi_id,
        extra_payload=row.extra_payload or {},
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def create_notification(
    db: Session,
    *,
    recipient_user_id: UUID,
    sender_user_id: UUID | None,
    event_type: str,
    severity: str,
    title: str,
    content: str,
    source_itinerary_id: UUID | None = None,
    forked_itinerary_id: UUID | None = None,
    source_snapshot_id: UUID | None = None,
    correction_id: UUID | None = None,
    poi_id: UUID | None = None,
    extra_payload: dict | None = None,
    dedupe_key: str | None = None,
) -> UserNotification | None:
    if dedupe_key and len(dedupe_key) > 128:
        digest = hashlib.sha256(dedupe_key.encode("utf-8")).hexdigest()[:48]
        dedupe_key = f"h:{digest}"

    if dedupe_key:
        scalar_result = db.scalars(
            select(UserNotification).where(UserNotification.dedupe_key == dedupe_key).limit(1)
        )
        if hasattr(scalar_result, "first"):
            exists = scalar_result.first()
        elif hasattr(scalar_result, "all"):
            rows = scalar_result.all()
            exists = rows[0] if rows else None
        else:
            exists = None
        if exists is not None:
            return None

    row = UserNotification(
        recipient_user_id=recipient_user_id,
        sender_user_id=sender_user_id,
        event_type=event_type,
        severity=severity,
        title=title,
        content=content,
        source_itinerary_id=source_itinerary_id,
        forked_itinerary_id=forked_itinerary_id,
        source_snapshot_id=source_snapshot_id,
        correction_id=correction_id,
        poi_id=poi_id,
        extra_payload=extra_payload or {},
        dedupe_key=dedupe_key,
    )
    db.add(row)
    if hasattr(db, "flush"):
        try:
            db.flush()
        except IntegrityError:
            return None
    return row


def list_notifications(
    db: Session,
    current_user: User,
    offset: int,
    limit: int,
    unread_only: bool,
) -> UserNotificationListResponse:
    base_stmt = select(UserNotification).where(UserNotification.recipient_user_id == current_user.id)
    if unread_only:
        base_stmt = base_stmt.where(UserNotification.is_read.is_(False))

    total = db.scalar(select(func.count()).select_from(base_stmt.subquery())) or 0
    unread_count = (
        db.scalar(
            select(func.count())
            .select_from(UserNotification)
            .where(
                UserNotification.recipient_user_id == current_user.id,
                UserNotification.is_read.is_(False),
            )
        )
        or 0
    )

    rows = db.scalars(
        base_stmt.order_by(UserNotification.created_at.desc()).offset(offset).limit(limit)
    ).all()
    return UserNotificationListResponse(
        items=[_to_response(row) for row in rows],
        total=total,
        unread_count=unread_count,
        offset=offset,
        limit=limit,
    )


def mark_notification_read(
    db: Session,
    notification_id: UUID,
    current_user: User,
    read: bool,
) -> UserNotificationResponse:
    row = db.get(UserNotification, notification_id)
    if row is None or row.recipient_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    row.is_read = read
    row.read_at = datetime.now(UTC) if read else None
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_response(row)


def mark_all_notifications_read(db: Session, current_user: User) -> MarkAllNotificationsReadResponse:
    now = datetime.now(UTC)
    result = db.execute(
        update(UserNotification)
        .where(UserNotification.recipient_user_id == current_user.id, UserNotification.is_read.is_(False))
        .values(is_read=True, read_at=now)
    )
    db.commit()
    return MarkAllNotificationsReadResponse(updated_count=result.rowcount or 0)


def _build_source_update_severity(
    changed_fields: set[str],
    has_removed_items: bool,
    has_modified_items: bool,
) -> str:
    if "visibility" in changed_fields or has_removed_items:
        return "critical"
    if has_modified_items:
        return "warning"
    return "info"


def notify_source_itinerary_updated(
    db: Session,
    *,
    source_itinerary_id: UUID,
    source_snapshot_id: UUID,
    sender_user_id: UUID,
    source_title: str,
    changed_fields: set[str],
    has_removed_items: bool,
    has_modified_items: bool,
) -> int:
    rows = db.execute(
        select(ItineraryFork.forked_itinerary_id, ItineraryFork.forked_by_user_id, Itinerary.status)
        .join(Itinerary, Itinerary.id == ItineraryFork.forked_itinerary_id)
        .where(ItineraryFork.source_itinerary_id == source_itinerary_id)
    ).all()
    severity = _build_source_update_severity(changed_fields, has_removed_items, has_modified_items)
    created = 0
    for forked_itinerary_id, recipient_user_id, fork_status in rows:
        if fork_status not in {"draft", "in_progress"}:
            continue
        dedupe_key = f"source_update:{recipient_user_id}:{source_snapshot_id}"
        record = create_notification(
            db,
            recipient_user_id=recipient_user_id,
            sender_user_id=sender_user_id,
            event_type="source_itinerary_updated",
            severity=severity,
            title="源行程已更新",
            content=f"你借鉴的《{source_title}》有新变更，建议查看最新对比。",
            source_itinerary_id=source_itinerary_id,
            forked_itinerary_id=forked_itinerary_id,
            source_snapshot_id=source_snapshot_id,
            extra_payload={"changed_fields": sorted(changed_fields)},
            dedupe_key=dedupe_key,
        )
        if record is not None:
            created += 1
    return created


def _severity_from_correction_type(type_code: str) -> str:
    if type_code == "temporary_closed":
        return "critical"
    if type_code in {"opening_hours_changed", "address_changed"}:
        return "warning"
    return "info"


def notify_correction_accepted(
    db: Session,
    *,
    correction: PoiCorrection,
    correction_type_code: str,
    reviewer_user_id: UUID,
    poi_name_snapshot: str | None,
) -> int:
    severity = _severity_from_correction_type(correction_type_code)
    created = 0
    poi_name = poi_name_snapshot or "景点"

    submitter_dedupe = f"correction_accepted:{correction.submitter_user_id}:{correction.id}"
    submitter_record = create_notification(
        db,
        recipient_user_id=correction.submitter_user_id,
        sender_user_id=reviewer_user_id,
        event_type="correction_accepted",
        severity=severity,
        title="纠错已被采纳",
        content=f"你提交的 {poi_name} 纠错已被采纳。",
        correction_id=correction.id,
        poi_id=correction.poi_id,
        extra_payload={"type_code": correction_type_code},
        dedupe_key=submitter_dedupe,
    )
    if submitter_record is not None:
        created += 1

    if not hasattr(db, "execute"):
        return created

    related_fork_rows = db.execute(
        select(Itinerary.creator_user_id, Itinerary.id)
        .join(ItineraryFork, ItineraryFork.forked_itinerary_id == Itinerary.id)
        .join(ItineraryItem, ItineraryItem.itinerary_id == Itinerary.id)
        .where(
            ItineraryItem.poi_id == correction.poi_id,
            Itinerary.status.in_(["draft", "in_progress"]),
        )
    ).all()
    seen_pair: set[tuple[UUID, UUID]] = set()
    for recipient_user_id, forked_itinerary_id in related_fork_rows:
        if recipient_user_id == correction.submitter_user_id:
            continue
        pair = (recipient_user_id, forked_itinerary_id)
        if pair in seen_pair:
            continue
        seen_pair.add(pair)
        dedupe_key = f"correction_accepted:{recipient_user_id}:{correction.id}:{forked_itinerary_id}"
        record = create_notification(
            db,
            recipient_user_id=recipient_user_id,
            sender_user_id=reviewer_user_id,
            event_type="correction_accepted",
            severity=severity,
            title="相关景点有新采纳纠错",
            content=f"{poi_name} 的信息已更新，建议复核你的行程。",
            correction_id=correction.id,
            poi_id=correction.poi_id,
            forked_itinerary_id=forked_itinerary_id,
            extra_payload={"type_code": correction_type_code},
            dedupe_key=dedupe_key,
        )
        if record is not None:
            created += 1
    return created