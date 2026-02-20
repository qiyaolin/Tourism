from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.poi import Poi
from app.models.poi_ticket_rule import PoiTicketRule
from app.models.pricing_audience import PricingAudience
from app.schemas.poi import (
    PoiCreate,
    PoiListResponse,
    PoiResponse,
    PoiTicketRuleBatchUpsert,
    PoiTicketRuleItem,
    PoiTicketRuleListResponse,
    PoiUpdate,
    PricingAudienceItem,
    PricingAudienceListResponse,
)


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
        ticket_rules=[],
        parent_poi_id=poi.parent_poi_id,
        created_at=poi.created_at,
        updated_at=poi.updated_at,
    )


def _rules_for_poi_ids(db: Session, poi_ids: list[UUID]) -> dict[UUID, list[PoiTicketRuleItem]]:
    if not poi_ids:
        return {}
    stmt = (
        select(PoiTicketRule, PricingAudience.label)
        .join(PricingAudience, PricingAudience.code == PoiTicketRule.audience_code)
        .where(PoiTicketRule.poi_id.in_(poi_ids), PoiTicketRule.is_active.is_(True))
        .order_by(PoiTicketRule.poi_id.asc(), PricingAudience.sort_order.asc(), PoiTicketRule.price.asc())
    )
    out: dict[UUID, list[PoiTicketRuleItem]] = {}
    for row in db.execute(stmt).all():
        if not isinstance(row, (tuple, list)) or len(row) != 2:
            continue
        rule, audience_label = row
        if not hasattr(rule, "poi_id"):
            continue
        out.setdefault(rule.poi_id, []).append(
            PoiTicketRuleItem(
                id=rule.id,
                audience_code=rule.audience_code,
                audience_label=audience_label,
                ticket_type=rule.ticket_type,
                time_slot=rule.time_slot,
                price=float(rule.price),
                currency=rule.currency,
                conditions=rule.conditions,
                is_active=rule.is_active,
            )
        )
    return out


def _refresh_poi_ticket_price_summary(db: Session, poi_id: UUID) -> None:
    min_price = db.scalar(
        select(func.min(PoiTicketRule.price)).where(
            PoiTicketRule.poi_id == poi_id,
            PoiTicketRule.is_active.is_(True),
        )
    )
    poi = db.get(Poi, poi_id)
    if poi is None:
        return
    poi.ticket_price = float(min_price) if min_price is not None else None
    db.add(poi)


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
    items = [_to_response(row) for row in rows]
    rules_map = _rules_for_poi_ids(db, [item.id for item in items])
    for item in items:
        item.ticket_rules = rules_map.get(item.id, [])
    return PoiListResponse(items=items, total=total, offset=offset, limit=limit)


def get_poi(db: Session, poi_id: UUID) -> PoiResponse:
    stmt = select(Poi, func.ST_AsText(Poi.geom)).where(Poi.id == poi_id)
    row = db.execute(stmt).one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POI not found")
    result = _to_response(row)
    result.ticket_rules = _rules_for_poi_ids(db, [result.id]).get(result.id, [])
    return result


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
    result = _to_response(row)
    result.ticket_rules = _rules_for_poi_ids(db, [result.id]).get(result.id, [])
    return result


def delete_poi(db: Session, poi_id: UUID) -> None:
    poi = db.get(Poi, poi_id)
    if poi is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POI not found")
    db.delete(poi)
    db.commit()


def list_pricing_audiences(db: Session) -> PricingAudienceListResponse:
    rows = db.scalars(
        select(PricingAudience)
        .where(PricingAudience.is_active.is_(True))
        .order_by(PricingAudience.sort_order.asc(), PricingAudience.created_at.asc())
    ).all()
    return PricingAudienceListResponse(
        items=[
            PricingAudienceItem(code=row.code, label=row.label, sort_order=row.sort_order)
            for row in rows
        ]
    )


def list_ticket_rules(db: Session, poi_id: UUID) -> PoiTicketRuleListResponse:
    poi = db.get(Poi, poi_id)
    if poi is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POI not found")
    rules = _rules_for_poi_ids(db, [poi_id]).get(poi_id, [])
    return PoiTicketRuleListResponse(items=rules)


def upsert_ticket_rules(
    db: Session,
    poi_id: UUID,
    payload: PoiTicketRuleBatchUpsert,
) -> PoiTicketRuleListResponse:
    poi = db.get(Poi, poi_id)
    if poi is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POI not found")
    audience_codes = {item.audience_code for item in payload.items}
    audience_count = db.scalar(
        select(func.count())
        .select_from(PricingAudience)
        .where(
            PricingAudience.code.in_(audience_codes),
            PricingAudience.is_active.is_(True),
        )
    ) or 0
    if audience_count != len(audience_codes):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid audience_code")

    existing = {
        row.id: row
        for row in db.scalars(select(PoiTicketRule).where(PoiTicketRule.poi_id == poi_id)).all()
    }
    keep_ids: set[UUID] = set()
    for item in payload.items:
        if item.id and item.id in existing:
            row = existing[item.id]
            keep_ids.add(row.id)
        else:
            row = PoiTicketRule(poi_id=poi_id)
            db.add(row)
            db.flush()
            keep_ids.add(row.id)
        row.audience_code = item.audience_code
        row.ticket_type = item.ticket_type.strip()
        row.time_slot = item.time_slot.strip()
        row.price = item.price
        row.currency = item.currency.strip().upper()
        row.conditions = item.conditions.strip() if item.conditions else None
        row.is_active = item.is_active
        row.source = "manual"
        db.add(row)

    for row in existing.values():
        if row.id not in keep_ids:
            db.delete(row)

    _refresh_poi_ticket_price_summary(db, poi_id)
    db.commit()
    return list_ticket_rules(db, poi_id)
