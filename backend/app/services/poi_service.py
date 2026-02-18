from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.poi import Poi
from app.schemas.poi import PoiCreate, PoiListResponse, PoiResponse, PoiUpdate


def _point_text(longitude: float, latitude: float) -> str:
    return f"POINT({longitude} {latitude})"


def _parse_point_text(value: str) -> tuple[float, float]:
    raw = value.strip().replace("POINT(", "").replace(")", "")
    lon, lat = raw.split(" ")
    return float(lon), float(lat)


def _to_response(row: tuple[Poi, str]) -> PoiResponse:
    poi, wkt = row
    lon, lat = _parse_point_text(wkt)
    return PoiResponse(
        id=poi.id,
        name=poi.name,
        type=poi.type,
        longitude=lon,
        latitude=lat,
        address=poi.address,
        opening_hours=poi.opening_hours,
        ticket_price=float(poi.ticket_price) if poi.ticket_price is not None else None,
        parent_poi_id=poi.parent_poi_id,
        created_at=poi.created_at,
        updated_at=poi.updated_at,
    )


def create_poi(db: Session, payload: PoiCreate) -> PoiResponse:
    poi = Poi(
        name=payload.name,
        type=payload.type,
        geom=_point_text(payload.longitude, payload.latitude),
        address=payload.address,
        opening_hours=payload.opening_hours,
        ticket_price=payload.ticket_price,
        parent_poi_id=payload.parent_poi_id,
    )
    db.add(poi)
    db.commit()
    stmt = select(Poi, func.ST_AsText(Poi.geom)).where(Poi.id == poi.id)
    row = db.execute(stmt).one()
    return _to_response(row)


def list_pois(db: Session, offset: int, limit: int) -> PoiListResponse:
    total = db.scalar(select(func.count()).select_from(Poi)) or 0
    stmt = select(Poi, func.ST_AsText(Poi.geom)).order_by(Poi.created_at.desc()).offset(offset).limit(limit)
    rows = db.execute(stmt).all()
    return PoiListResponse(items=[_to_response(row) for row in rows], total=total, offset=offset, limit=limit)


def get_poi(db: Session, poi_id: UUID) -> PoiResponse:
    stmt = select(Poi, func.ST_AsText(Poi.geom)).where(Poi.id == poi_id)
    row = db.execute(stmt).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POI not found")
    return _to_response(row)


def update_poi(db: Session, poi_id: UUID, payload: PoiUpdate) -> PoiResponse:
    poi = db.get(Poi, poi_id)
    if poi is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POI not found")
    data = payload.model_dump(exclude_unset=True)
    lon = data.pop("longitude", None)
    lat = data.pop("latitude", None)
    if (lon is None) ^ (lat is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="longitude and latitude must be updated together",
        )
    for key, value in data.items():
        setattr(poi, key, value)
    if lon is not None and lat is not None:
        poi.geom = _point_text(lon, lat)
    db.add(poi)
    db.commit()
    stmt = select(Poi, func.ST_AsText(Poi.geom)).where(Poi.id == poi.id)
    row = db.execute(stmt).one()
    return _to_response(row)


def delete_poi(db: Session, poi_id: UUID) -> None:
    poi = db.get(Poi, poi_id)
    if poi is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POI not found")
    db.delete(poi)
    db.commit()
