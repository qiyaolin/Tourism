from datetime import time
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from app.models.itinerary import Itinerary
from app.models.itinerary_diff_action import ItineraryDiffAction
from app.models.itinerary_fork import ItineraryFork
from app.models.itinerary_item import ItineraryItem
from app.models.itinerary_snapshot import ItinerarySnapshot
from app.models.poi import Poi
from app.models.user import User
from app.schemas.itinerary import (
    ForkItineraryResponse,
    ItineraryCreate,
    ItineraryDiffActionBatchRequest,
    ItineraryDiffActionBatchResponse,
    ItineraryDiffActionStatusItem,
    ItineraryDiffActionStatusResponse,
    ItineraryDiffItemAdded,
    ItineraryDiffItemModified,
    ItineraryDiffItemRemoved,
    ItineraryDiffResponse,
    ItineraryDiffSummary,
    ItineraryFieldDiff,
    ItineraryItemCreate,
    ItineraryItemPoiSnapshot,
    ItineraryItemResponse,
    ItineraryItemsWithPoiListResponse,
    ItineraryItemUpdate,
    ItineraryItemWithPoiResponse,
    ItineraryListResponse,
    ItineraryResponse,
    ItineraryUpdate,
    PublicItineraryListResponse,
    PublicItineraryResponse,
)

_META_DIFF_FIELDS = ("title", "destination", "days", "status", "visibility", "cover_image_url")
_ITEM_DIFF_FIELDS = (
    "day_index",
    "sort_order",
    "poi_id",
    "poi_name",
    "poi_type",
    "longitude",
    "latitude",
    "address",
    "opening_hours",
    "ticket_price",
    "start_time",
    "duration_minutes",
    "cost",
    "tips",
)
_DIFF_ACTIONS = {"applied", "rolled_back", "ignored", "read"}


def _ensure_status(value: str) -> str:
    if value not in {"draft", "in_progress", "published"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid itinerary status",
        )
    return value


def _ensure_visibility(value: str) -> str:
    if value not in {"private", "public", "followers"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid itinerary visibility",
        )
    return value


def _item_to_response(item: ItineraryItem) -> ItineraryItemResponse:
    return ItineraryItemResponse(
        id=item.id,
        itinerary_id=item.itinerary_id,
        day_index=item.day_index,
        sort_order=item.sort_order,
        poi_id=item.poi_id,
        start_time=item.start_time,
        duration_minutes=item.duration_minutes,
        cost=float(item.cost) if item.cost is not None else None,
        tips=item.tips,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _itinerary_to_response(
    row: Itinerary,
    fork_meta: tuple[UUID, str, str] | None = None,
) -> ItineraryResponse:
    source_id = fork_meta[0] if fork_meta else None
    source_nickname = fork_meta[1] if fork_meta else None
    source_title = fork_meta[2] if fork_meta else None
    return ItineraryResponse(
        id=row.id,
        title=row.title,
        destination=row.destination,
        days=row.days,
        creator_user_id=row.creator_user_id,
        status=row.status,
        visibility=row.visibility,
        cover_image_url=row.cover_image_url,
        fork_source_itinerary_id=source_id,
        fork_source_author_nickname=source_nickname,
        fork_source_title=source_title,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _public_itinerary_to_response(
    row: Itinerary,
    author_nickname: str,
    forked_count: int = 0,
) -> PublicItineraryResponse:
    return PublicItineraryResponse(
        id=row.id,
        title=row.title,
        destination=row.destination,
        days=row.days,
        status=row.status,
        visibility=row.visibility,
        cover_image_url=row.cover_image_url,
        author_nickname=author_nickname,
        forked_count=forked_count,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _parse_point_text(value: str) -> tuple[float, float]:
    raw = value.strip().removeprefix("POINT(").removesuffix(")")
    lon_str, lat_str = raw.split(" ", maxsplit=1)
    return float(lon_str), float(lat_str)


def _get_fork_source_meta_map(
    db: Session,
    forked_itinerary_ids: list[UUID],
) -> dict[UUID, tuple[UUID, str, str]]:
    if not forked_itinerary_ids:
        return {}
    source_itinerary = aliased(Itinerary)
    source_author = aliased(User)
    stmt = (
        select(
            ItineraryFork.forked_itinerary_id,
            ItineraryFork.source_itinerary_id,
            source_author.nickname,
            source_itinerary.title,
        )
        .join(source_itinerary, source_itinerary.id == ItineraryFork.source_itinerary_id)
        .join(source_author, source_author.id == source_itinerary.creator_user_id)
        .where(ItineraryFork.forked_itinerary_id.in_(forked_itinerary_ids))
    )
    rows = db.execute(stmt).all()
    return {
        forked_id: (source_id, nickname, title)
        for forked_id, source_id, nickname, title in rows
    }


def _snapshot_item_dict(
    item: ItineraryItem,
    poi: Poi,
    poi_wkt: str,
) -> dict[str, Any]:
    longitude, latitude = _parse_point_text(poi_wkt)
    return {
        "day_index": item.day_index,
        "sort_order": item.sort_order,
        "poi_id": str(poi.id),
        "poi_name": poi.name,
        "poi_type": poi.type,
        "longitude": longitude,
        "latitude": latitude,
        "address": poi.address,
        "opening_hours": poi.opening_hours,
        "ticket_price": float(poi.ticket_price) if poi.ticket_price is not None else None,
        "start_time": item.start_time.isoformat() if item.start_time is not None else None,
        "duration_minutes": item.duration_minutes,
        "cost": float(item.cost) if item.cost is not None else None,
        "tips": item.tips,
    }


def _build_snapshot_payload(db: Session, itinerary: Itinerary) -> dict[str, Any]:
    stmt = (
        select(ItineraryItem, Poi, func.ST_AsText(Poi.geom))
        .join(Poi, Poi.id == ItineraryItem.poi_id)
        .where(ItineraryItem.itinerary_id == itinerary.id)
        .order_by(ItineraryItem.day_index.asc(), ItineraryItem.sort_order.asc())
    )
    rows = db.execute(stmt).all()
    return {
        "meta": {
            "title": itinerary.title,
            "destination": itinerary.destination,
            "days": itinerary.days,
            "status": itinerary.status,
            "visibility": itinerary.visibility,
            "cover_image_url": itinerary.cover_image_url,
        },
        "items": [_snapshot_item_dict(item, poi, poi_wkt) for item, poi, poi_wkt in rows],
    }


def _create_snapshot_for_itinerary(db: Session, itinerary: Itinerary) -> ItinerarySnapshot:
    latest_version = (
        db.scalar(
            select(func.max(ItinerarySnapshot.version_no)).where(
                ItinerarySnapshot.itinerary_id == itinerary.id
            )
        )
        or 0
    )
    snapshot = ItinerarySnapshot(
        itinerary_id=itinerary.id,
        version_no=latest_version + 1,
        snapshot_json=_build_snapshot_payload(db, itinerary),
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def _ensure_public_itinerary(db: Session, itinerary_id: UUID) -> tuple[Itinerary, str]:
    stmt = (
        select(Itinerary, User.nickname)
        .join(User, User.id == Itinerary.creator_user_id)
        .where(
            Itinerary.id == itinerary_id,
            Itinerary.status == "published",
            Itinerary.visibility == "public",
        )
        .limit(1)
    )
    row = db.execute(stmt).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    return row


def _item_key(item: dict[str, Any]) -> str:
    return f"d{item['day_index']}-s{item['sort_order']}"


def _field_diffs(
    before_obj: dict[str, Any],
    after_obj: dict[str, Any],
    fields: tuple[str, ...],
) -> list[ItineraryFieldDiff]:
    diffs: list[ItineraryFieldDiff] = []
    for field in fields:
        before_value = before_obj.get(field)
        after_value = after_obj.get(field)
        if before_value != after_value:
            diffs.append(ItineraryFieldDiff(field=field, before=before_value, after=after_value))
    return diffs


def _latest_source_snapshot_id(db: Session, source_itinerary_id: UUID) -> UUID | None:
    stmt = (
        select(ItinerarySnapshot.id)
        .where(ItinerarySnapshot.itinerary_id == source_itinerary_id)
        .order_by(ItinerarySnapshot.version_no.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()


def _build_action_status_map(
    db: Session,
    itinerary_id: UUID,
    source_snapshot_id: UUID,
    actor_user_id: UUID,
) -> dict[str, str]:
    stmt = (
        select(ItineraryDiffAction)
        .where(
            ItineraryDiffAction.itinerary_id == itinerary_id,
            ItineraryDiffAction.source_snapshot_id == source_snapshot_id,
            ItineraryDiffAction.actor_user_id == actor_user_id,
        )
        .order_by(ItineraryDiffAction.created_at.desc())
    )
    rows = db.scalars(stmt).all()
    result: dict[str, str] = {}
    for row in rows:
        if row.diff_key in result:
            continue
        result[row.diff_key] = row.action
    return result


def _parse_start_time(value: Any) -> time | None:
    if value is None:
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        try:
            return time.fromisoformat(value)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_time in snapshot",
            ) from exc
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid start_time in snapshot",
    )


def create_itinerary(db: Session, creator: User, payload: ItineraryCreate) -> ItineraryResponse:
    status_value = _ensure_status(payload.status)
    visibility_value = _ensure_visibility(payload.visibility)
    itinerary = Itinerary(
        title=payload.title,
        destination=payload.destination,
        days=payload.days,
        creator_user_id=creator.id,
        status=status_value,
        visibility=visibility_value,
        cover_image_url=payload.cover_image_url,
    )
    db.add(itinerary)
    db.commit()
    db.refresh(itinerary)
    return _itinerary_to_response(itinerary)


def list_itineraries(db: Session, creator: User, offset: int, limit: int) -> ItineraryListResponse:
    base = select(Itinerary).where(Itinerary.creator_user_id == creator.id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(base.order_by(Itinerary.created_at.desc()).offset(offset).limit(limit)).all()
    meta_map = _get_fork_source_meta_map(db, [row.id for row in rows])
    return ItineraryListResponse(
        items=[_itinerary_to_response(row, meta_map.get(row.id)) for row in rows],
        total=total,
        offset=offset,
        limit=limit,
    )


def get_itinerary(db: Session, itinerary_id: UUID, creator: User) -> ItineraryResponse:
    row = db.get(Itinerary, itinerary_id)
    if row is None or row.creator_user_id != creator.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    meta_map = _get_fork_source_meta_map(db, [row.id])
    return _itinerary_to_response(row, meta_map.get(row.id))


def list_public_itineraries(db: Session, offset: int, limit: int) -> PublicItineraryListResponse:
    conditions = (
        Itinerary.status == "published",
        Itinerary.visibility == "public",
    )
    base = (
        select(Itinerary, User.nickname)
        .join(User, User.id == Itinerary.creator_user_id)
        .where(*conditions)
    )
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.execute(base.order_by(Itinerary.created_at.desc()).offset(offset).limit(limit)).all()
    return PublicItineraryListResponse(
        items=[_public_itinerary_to_response(itinerary, nickname) for itinerary, nickname in rows],
        total=total,
        offset=offset,
        limit=limit,
    )


def get_public_itinerary(db: Session, itinerary_id: UUID) -> PublicItineraryResponse:
    itinerary, nickname = _ensure_public_itinerary(db, itinerary_id)
    return _public_itinerary_to_response(itinerary, nickname)


def fork_public_itinerary(
    db: Session,
    source_itinerary_id: UUID,
    current_user: User,
) -> ForkItineraryResponse:
    source_itinerary = db.get(Itinerary, source_itinerary_id)
    if source_itinerary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")

    source_author = db.get(User, source_itinerary.creator_user_id)
    if source_author is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Itinerary author not found",
        )

    if source_itinerary.status == "published" and source_itinerary.visibility == "public":
        snapshot = _create_snapshot_for_itinerary(db, source_itinerary)
        db.commit()
        db.refresh(snapshot)
    else:
        stmt = (
            select(ItinerarySnapshot)
            .where(ItinerarySnapshot.itinerary_id == source_itinerary.id)
            .order_by(ItinerarySnapshot.version_no.desc())
            .limit(1)
        )
        snapshot = db.scalars(stmt).first()
        if snapshot is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Itinerary is not available for fork",
            )

    snapshot_meta = snapshot.snapshot_json.get("meta", {})
    snapshot_items = snapshot.snapshot_json.get("items", [])

    new_itinerary = Itinerary(
        title=f"来自@{source_author.nickname}：{source_itinerary.title}",
        destination=str(snapshot_meta.get("destination") or source_itinerary.destination),
        days=int(snapshot_meta.get("days") or source_itinerary.days),
        creator_user_id=current_user.id,
        status="in_progress",
        visibility="private",
        cover_image_url=snapshot_meta.get("cover_image_url"),
    )
    db.add(new_itinerary)
    db.flush()

    for payload in snapshot_items:
        db.add(
            ItineraryItem(
                itinerary_id=new_itinerary.id,
                day_index=int(payload["day_index"]),
                sort_order=int(payload["sort_order"]),
                poi_id=UUID(str(payload["poi_id"])),
                start_time=_parse_start_time(payload.get("start_time")),
                duration_minutes=payload.get("duration_minutes"),
                cost=payload.get("cost"),
                tips=payload.get("tips"),
            )
        )

    db.add(
        ItineraryFork(
            source_itinerary_id=source_itinerary.id,
            forked_itinerary_id=new_itinerary.id,
            forked_by_user_id=current_user.id,
            source_snapshot_id=snapshot.id,
        )
    )
    db.commit()

    return ForkItineraryResponse(
        new_itinerary_id=new_itinerary.id,
        title=new_itinerary.title,
        source_itinerary_id=source_itinerary.id,
        source_author_nickname=source_author.nickname,
        source_title=source_itinerary.title,
    )


def get_itinerary_diff(db: Session, itinerary_id: UUID, creator: User) -> ItineraryDiffResponse:
    itinerary = db.get(Itinerary, itinerary_id)
    if itinerary is None or itinerary.creator_user_id != creator.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")

    fork_stmt = (
        select(ItineraryFork)
        .where(
            ItineraryFork.forked_itinerary_id == itinerary_id,
            ItineraryFork.forked_by_user_id == creator.id,
        )
        .limit(1)
    )
    fork_rel = db.scalars(fork_stmt).first()
    if fork_rel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fork relation not found")

    source_snapshot = db.get(ItinerarySnapshot, fork_rel.source_snapshot_id)
    if source_snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot not found")

    current_payload = _build_snapshot_payload(db, itinerary)
    source_payload = source_snapshot.snapshot_json

    meta_diffs = _field_diffs(
        source_payload.get("meta", {}),
        current_payload.get("meta", {}),
        _META_DIFF_FIELDS,
    )

    source_items = source_payload.get("items", [])
    current_items = current_payload.get("items", [])
    source_map = {_item_key(item): item for item in source_items}
    current_map = {_item_key(item): item for item in current_items}

    added_items: list[ItineraryDiffItemAdded] = []
    removed_items: list[ItineraryDiffItemRemoved] = []
    modified_items: list[ItineraryDiffItemModified] = []

    for key in sorted(current_map.keys() - source_map.keys()):
        added_items.append(ItineraryDiffItemAdded(key=key, current=current_map[key]))
    for key in sorted(source_map.keys() - current_map.keys()):
        removed_items.append(ItineraryDiffItemRemoved(key=key, source=source_map[key]))
    for key in sorted(source_map.keys() & current_map.keys()):
        item_diffs = _field_diffs(source_map[key], current_map[key], _ITEM_DIFF_FIELDS)
        if item_diffs:
            modified_items.append(ItineraryDiffItemModified(key=key, fields=item_diffs))

    return ItineraryDiffResponse(
        source_snapshot_id=source_snapshot.id,
        source_itinerary_id=fork_rel.source_itinerary_id,
        forked_itinerary_id=itinerary.id,
        summary=ItineraryDiffSummary(
            added=len(added_items),
            removed=len(removed_items),
            modified=len(modified_items),
        ),
        metadata_diffs=meta_diffs,
        added_items=added_items,
        removed_items=removed_items,
        modified_items=modified_items,
    )


def list_items_with_poi(
    db: Session, itinerary_id: UUID, creator: User
) -> ItineraryItemsWithPoiListResponse:
    itinerary = db.get(Itinerary, itinerary_id)
    if itinerary is None or itinerary.creator_user_id != creator.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")

    stmt = (
        select(ItineraryItem, Poi, func.ST_AsText(Poi.geom))
        .join(Poi, Poi.id == ItineraryItem.poi_id)
        .where(ItineraryItem.itinerary_id == itinerary_id)
        .order_by(ItineraryItem.day_index.asc(), ItineraryItem.sort_order.asc())
    )
    rows = db.execute(stmt).all()

    items = []
    for item, poi, poi_wkt in rows:
        longitude, latitude = _parse_point_text(poi_wkt)
        items.append(
            ItineraryItemWithPoiResponse(
                item_id=item.id,
                itinerary_id=item.itinerary_id,
                day_index=item.day_index,
                sort_order=item.sort_order,
                start_time=item.start_time,
                duration_minutes=item.duration_minutes,
                cost=float(item.cost) if item.cost is not None else None,
                tips=item.tips,
                poi=ItineraryItemPoiSnapshot(
                    id=poi.id,
                    name=poi.name,
                    type=poi.type,
                    longitude=longitude,
                    latitude=latitude,
                    address=poi.address,
                    opening_hours=poi.opening_hours,
                    ticket_price=float(poi.ticket_price) if poi.ticket_price is not None else None,
                ),
            )
        )
    return ItineraryItemsWithPoiListResponse(items=items)


def list_public_items_with_poi(
    db: Session, itinerary_id: UUID
) -> ItineraryItemsWithPoiListResponse:
    itinerary = db.get(Itinerary, itinerary_id)
    if itinerary is None or itinerary.status != "published" or itinerary.visibility != "public":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    stmt = (
        select(ItineraryItem, Poi, func.ST_AsText(Poi.geom))
        .join(Poi, Poi.id == ItineraryItem.poi_id)
        .where(ItineraryItem.itinerary_id == itinerary_id)
        .order_by(ItineraryItem.day_index.asc(), ItineraryItem.sort_order.asc())
    )
    rows = db.execute(stmt).all()

    items = []
    for item, poi, poi_wkt in rows:
        longitude, latitude = _parse_point_text(poi_wkt)
        items.append(
            ItineraryItemWithPoiResponse(
                item_id=item.id,
                itinerary_id=item.itinerary_id,
                day_index=item.day_index,
                sort_order=item.sort_order,
                start_time=item.start_time,
                duration_minutes=item.duration_minutes,
                cost=float(item.cost) if item.cost is not None else None,
                tips=item.tips,
                poi=ItineraryItemPoiSnapshot(
                    id=poi.id,
                    name=poi.name,
                    type=poi.type,
                    longitude=longitude,
                    latitude=latitude,
                    address=poi.address,
                    opening_hours=poi.opening_hours,
                    ticket_price=float(poi.ticket_price) if poi.ticket_price is not None else None,
                ),
            )
        )
    return ItineraryItemsWithPoiListResponse(items=items)


def update_itinerary(
    db: Session,
    itinerary_id: UUID,
    creator: User,
    payload: ItineraryUpdate,
) -> ItineraryResponse:
    row = db.get(Itinerary, itinerary_id)
    if row is None or row.creator_user_id != creator.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    data = payload.model_dump(exclude_unset=True)
    old_status = row.status
    if "status" in data:
        data["status"] = _ensure_status(data["status"])
    if "visibility" in data:
        data["visibility"] = _ensure_visibility(data["visibility"])
    for key, value in data.items():
        setattr(row, key, value)
    db.add(row)
    db.commit()
    db.refresh(row)

    should_snapshot = False
    if row.status == "published":
        if old_status != "published":
            should_snapshot = True
        else:
            should_snapshot = any(
                field in data
                for field in (
                    "title",
                    "destination",
                    "days",
                    "visibility",
                    "cover_image_url",
                )
            )
    if should_snapshot:
        _create_snapshot_for_itinerary(db, row)
        db.commit()

    meta_map = _get_fork_source_meta_map(db, [row.id])
    return _itinerary_to_response(row, meta_map.get(row.id))


def delete_itinerary(db: Session, itinerary_id: UUID, creator: User) -> None:
    row = db.get(Itinerary, itinerary_id)
    if row is None or row.creator_user_id != creator.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    db.delete(row)
    db.commit()


def create_item(
    db: Session,
    itinerary_id: UUID,
    creator: User,
    payload: ItineraryItemCreate,
) -> ItineraryItemResponse:
    itinerary = db.get(Itinerary, itinerary_id)
    if itinerary is None or itinerary.creator_user_id != creator.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    if payload.day_index > itinerary.days:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="day_index out of itinerary range",
        )
    if db.get(Poi, payload.poi_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="poi_id not found")
    should_snapshot = itinerary.status == "published"
    if itinerary.status == "draft":
        itinerary.status = "in_progress"
        db.add(itinerary)
    item = ItineraryItem(
        itinerary_id=itinerary_id,
        day_index=payload.day_index,
        sort_order=payload.sort_order,
        poi_id=payload.poi_id,
        start_time=payload.start_time,
        duration_minutes=payload.duration_minutes,
        cost=payload.cost,
        tips=payload.tips,
    )
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate day_index and sort_order",
        ) from exc
    if should_snapshot:
        _create_snapshot_for_itinerary(db, itinerary)
        db.commit()
    db.refresh(item)
    return _item_to_response(item)


def update_item(
    db: Session,
    itinerary_id: UUID,
    item_id: UUID,
    creator: User,
    payload: ItineraryItemUpdate,
) -> ItineraryItemResponse:
    itinerary = db.get(Itinerary, itinerary_id)
    if itinerary is None or itinerary.creator_user_id != creator.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    item = db.get(ItineraryItem, item_id)
    if item is None or item.itinerary_id != itinerary_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary item not found"
        )
    data = payload.model_dump(exclude_unset=True)
    if "day_index" in data and data["day_index"] > itinerary.days:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="day_index out of itinerary range",
        )
    if "poi_id" in data and db.get(Poi, data["poi_id"]) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="poi_id not found")
    for key, value in data.items():
        setattr(item, key, value)
    db.add(item)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate day_index and sort_order",
        ) from exc
    if itinerary.status == "published":
        _create_snapshot_for_itinerary(db, itinerary)
        db.commit()
    db.refresh(item)
    return _item_to_response(item)


def delete_item(db: Session, itinerary_id: UUID, item_id: UUID, creator: User) -> None:
    itinerary = db.get(Itinerary, itinerary_id)
    if itinerary is None or itinerary.creator_user_id != creator.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    item = db.get(ItineraryItem, item_id)
    if item is None or item.itinerary_id != itinerary_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary item not found"
        )
    db.delete(item)
    db.commit()
    if itinerary.status == "published":
        _create_snapshot_for_itinerary(db, itinerary)
        db.commit()
