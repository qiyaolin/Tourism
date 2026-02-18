from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.itinerary import Itinerary
from app.models.itinerary_item import ItineraryItem
from app.models.poi import Poi
from app.models.user import User
from app.schemas.itinerary import (
    ItineraryCreate,
    ItineraryItemCreate,
    ItineraryItemPoiSnapshot,
    ItineraryItemResponse,
    ItineraryItemsWithPoiListResponse,
    ItineraryItemUpdate,
    ItineraryItemWithPoiResponse,
    ItineraryListResponse,
    ItineraryResponse,
    ItineraryUpdate,
)


def _ensure_status(value: str) -> str:
    if value not in {"draft", "published"}:
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


def _itinerary_to_response(row: Itinerary) -> ItineraryResponse:
    return ItineraryResponse(
        id=row.id,
        title=row.title,
        destination=row.destination,
        days=row.days,
        creator_user_id=row.creator_user_id,
        status=row.status,
        visibility=row.visibility,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _parse_point_text(value: str) -> tuple[float, float]:
    raw = value.strip().removeprefix("POINT(").removesuffix(")")
    lon_str, lat_str = raw.split(" ", maxsplit=1)
    return float(lon_str), float(lat_str)


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
    )
    db.add(itinerary)
    db.commit()
    db.refresh(itinerary)
    return _itinerary_to_response(itinerary)


def list_itineraries(db: Session, creator: User, offset: int, limit: int) -> ItineraryListResponse:
    base = select(Itinerary).where(Itinerary.creator_user_id == creator.id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(base.order_by(Itinerary.created_at.desc()).offset(offset).limit(limit)).all()
    return ItineraryListResponse(
        items=[_itinerary_to_response(row) for row in rows],
        total=total,
        offset=offset,
        limit=limit,
    )


def get_itinerary(db: Session, itinerary_id: UUID, creator: User) -> ItineraryResponse:
    row = db.get(Itinerary, itinerary_id)
    if row is None or row.creator_user_id != creator.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    return _itinerary_to_response(row)


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
    if "status" in data:
        data["status"] = _ensure_status(data["status"])
    if "visibility" in data:
        data["visibility"] = _ensure_visibility(data["visibility"])
    for key, value in data.items():
        setattr(row, key, value)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _itinerary_to_response(row)


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
