import json
import re
from datetime import UTC, datetime
from io import BytesIO
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.itinerary import Itinerary
from app.models.itinerary_item import ItineraryItem
from app.models.poi import Poi
from app.models.poi_correction import PoiCorrection
from app.models.poi_correction_notification import PoiCorrectionNotification
from app.models.poi_correction_type import PoiCorrectionType
from app.models.poi_ticket_rule import PoiTicketRule
from app.models.pricing_audience import PricingAudience
from app.models.user import User
from app.schemas.poi_correction import (
    PoiCorrectionListResponse,
    PoiCorrectionResponse,
    PoiCorrectionReviewResponse,
    PoiCorrectionTypeListResponse,
    PoiCorrectionTypeResponse,
)
from app.services.notification_service import notify_correction_accepted
from app.services.storage import get_storage_provider

_ALLOWED_IMAGE_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
_POI_MUTABLE_FIELDS = {
    "ticket_price",
    "opening_hours",
    "address",
}
_OPENING_HOURS_PATTERN = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)-([01]\d|2[0-3]):([0-5]\d)$")


def _default_type_meta(code: str) -> tuple[str, dict | None, str | None]:
    if code == "ticket_price_changed":
        return (
            "ticket_rules",
            {
                "columns": ["audience_code", "ticket_type", "time_slot", "conditions", "price"],
                "currency": "CNY",
            },
            "按人群逐条填写票种、适用时段、使用条件和票价，审核通过后可直接应用。",
        )
    if code == "opening_hours_changed":
        return (
            "time_range",
            {"format": "HH:MM-HH:MM", "timezone": "local"},
            "请使用 24 小时制时间段（如 09:00-18:00）。",
        )
    return ("text", None, None)


def _to_type_response(row: PoiCorrectionType) -> PoiCorrectionTypeResponse:
    default_input_mode, default_input_schema, default_help_text = _default_type_meta(row.code)
    return PoiCorrectionTypeResponse(
        id=row.id,
        code=row.code,
        label=row.label,
        target_field=row.target_field,
        value_kind=row.value_kind,
        placeholder=row.placeholder,
        input_mode=row.input_mode or default_input_mode,
        input_schema=row.input_schema if row.input_schema is not None else default_input_schema,
        help_text=row.help_text or default_help_text,
        sort_order=row.sort_order,
    )


def _to_response(row: PoiCorrection, correction_type: PoiCorrectionType) -> PoiCorrectionResponse:
    return PoiCorrectionResponse(
        id=row.id,
        poi_id=row.poi_id,
        source_poi_name_snapshot=row.source_poi_name_snapshot,
        source_itinerary_id=row.source_itinerary_id,
        source_itinerary_title_snapshot=row.source_itinerary_title_snapshot,
        source_itinerary_author_snapshot=row.source_itinerary_author_snapshot,
        type_code=correction_type.code,
        type_label=correction_type.label,
        target_field=correction_type.target_field,
        value_kind=correction_type.value_kind,
        proposed_value=row.proposed_value,
        details=row.details,
        photo_url=row.photo_url,
        status=row.status,
        submitter_user_id=row.submitter_user_id,
        reviewer_user_id=row.reviewer_user_id,
        review_comment=row.review_comment,
        created_at=row.created_at,
        updated_at=row.updated_at,
        reviewed_at=row.reviewed_at,
    )


def _validate_image_upload(photo: UploadFile) -> tuple[str, str]:
    content_type = (photo.content_type or "").strip().lower()
    extension = _ALLOWED_IMAGE_TYPES.get(content_type)
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG/PNG/WEBP images are supported",
        )
    return content_type, extension


def strip_exif_bytes(raw_bytes: bytes, image_format: str) -> bytes:
    source = BytesIO(raw_bytes)
    with Image.open(source) as img:
        cleaned = img.copy()
        output = BytesIO()
        format_name = "JPEG" if image_format.lower() in {"jpg", "jpeg"} else image_format.upper()
        save_kwargs = {"format": format_name}
        if format_name == "JPEG":
            save_kwargs["quality"] = 88
            save_kwargs["optimize"] = True
        cleaned.save(output, **save_kwargs)
        return output.getvalue()


def _resolve_reviewer_user_id(db: Session, poi_id: UUID, submitter_user_id: UUID) -> UUID | None:
    stmt = (
        select(Itinerary.creator_user_id)
        .join(ItineraryItem, ItineraryItem.itinerary_id == Itinerary.id)
        .where(
            ItineraryItem.poi_id == poi_id,
            Itinerary.creator_user_id != submitter_user_id,
        )
        .order_by(Itinerary.updated_at.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()


def _parse_value_by_kind(raw_value: str | None, value_kind: str) -> str | float | None:
    if raw_value is None:
        return None
    cleaned = raw_value.strip()
    if not cleaned:
        return None
    if value_kind == "number":
        try:
            return float(cleaned)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid numeric correction value",
            ) from exc
    return cleaned


def _normalize_proposed_value(
    correction_type: PoiCorrectionType,
    raw_value: str | None,
) -> str | float | None:
    parsed = _parse_value_by_kind(raw_value, correction_type.value_kind)
    if parsed is None:
        return None
    if correction_type.code == "opening_hours_changed" and isinstance(parsed, str):
        normalized = parsed.strip()
        matched = _OPENING_HOURS_PATTERN.fullmatch(normalized)
        if matched is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="opening_hours must be in HH:MM-HH:MM format",
            )
        start_minutes = int(matched.group(1)) * 60 + int(matched.group(2))
        end_minutes = int(matched.group(3)) * 60 + int(matched.group(4))
        if end_minutes <= start_minutes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="opening_hours end time must be later than start time",
            )
        return normalized
    return parsed


def _parse_ticket_rules(raw_value: str | None) -> list[dict[str, object]]:
    if raw_value is None:
        return []
    text = raw_value.strip()
    if not text:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    rules: list[dict[str, object]] = []
    for row in data:
        if not isinstance(row, dict):
            continue
        audience_code = str(row.get("audience_code", "")).strip()
        ticket_type = str(row.get("ticket_type", "")).strip()
        time_slot = str(row.get("time_slot", "")).strip()
        currency = str(row.get("currency", "CNY")).strip().upper() or "CNY"
        conditions_raw = row.get("conditions")
        conditions = str(conditions_raw).strip() if conditions_raw is not None else None
        try:
            price = float(row.get("price", 0))
        except (TypeError, ValueError):
            continue
        if not audience_code or not ticket_type or not time_slot or price < 0:
            continue
        rules.append(
            {
                "audience_code": audience_code,
                "ticket_type": ticket_type,
                "time_slot": time_slot,
                "price": price,
                "currency": currency,
                "conditions": conditions if conditions else None,
            }
        )
    return rules


def list_correction_types(db: Session) -> PoiCorrectionTypeListResponse:
    stmt = (
        select(PoiCorrectionType)
        .where(PoiCorrectionType.is_active.is_(True))
        .order_by(PoiCorrectionType.sort_order.asc(), PoiCorrectionType.created_at.asc())
    )
    rows = db.scalars(stmt).all()
    return PoiCorrectionTypeListResponse(items=[_to_type_response(row) for row in rows])


async def submit_correction(
    db: Session,
    current_user: User,
    poi_id: UUID,
    type_code: str,
    proposed_value: str | None,
    details: str | None,
    photo: UploadFile | None,
    source_itinerary_id: UUID | None = None,
) -> PoiCorrectionResponse:
    poi = db.get(Poi, poi_id)
    if poi is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POI not found")

    correction_type = db.scalars(
        select(PoiCorrectionType)
        .where(PoiCorrectionType.code == type_code.strip(), PoiCorrectionType.is_active.is_(True))
        .limit(1)
    ).first()
    if correction_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid correction type"
        )

    parsed_rules = _parse_ticket_rules(proposed_value)
    parsed_value: str | float | None = None
    if correction_type.target_field != "ticket_price" or not parsed_rules:
        parsed_value = _normalize_proposed_value(correction_type, proposed_value)
    if correction_type.target_field in _POI_MUTABLE_FIELDS and parsed_value is None and not parsed_rules:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="proposed_value is required for selected correction type",
        )

    photo_url: str | None = None
    photo_storage_key: str | None = None
    if photo is not None:
        content_type, extension = _validate_image_upload(photo)
        raw = await photo.read()
        if not raw:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Photo file is empty"
            )
        cleaned = strip_exif_bytes(raw, extension)
        storage = get_storage_provider()
        photo_storage_key, photo_url = storage.save_bytes(
            content=cleaned,
            extension=extension,
            content_type=content_type,
        )

    reviewer_user_id = _resolve_reviewer_user_id(db, poi_id, current_user.id)
    source_itinerary_title_snapshot: str | None = None
    source_itinerary_author_snapshot: str | None = None
    if source_itinerary_id is not None:
        source_itinerary = db.get(Itinerary, source_itinerary_id)
        if source_itinerary is not None:
            source_itinerary_title_snapshot = source_itinerary.title
            source_author = db.get(User, source_itinerary.creator_user_id)
            source_itinerary_author_snapshot = source_author.nickname if source_author else None

    correction = PoiCorrection(
        poi_id=poi.id,
        type_id=correction_type.id,
        submitter_user_id=current_user.id,
        reviewer_user_id=reviewer_user_id,
        status="pending",
        proposed_value=proposed_value.strip() if proposed_value else None,
        details=details.strip() if details else None,
        source_poi_name_snapshot=poi.name,
        source_itinerary_id=source_itinerary_id,
        source_itinerary_title_snapshot=source_itinerary_title_snapshot,
        source_itinerary_author_snapshot=source_itinerary_author_snapshot,
        photo_url=photo_url,
        photo_storage_key=photo_storage_key,
    )
    db.add(correction)
    db.flush()

    if reviewer_user_id is not None:
        db.add(
            PoiCorrectionNotification(
                correction_id=correction.id,
                recipient_user_id=reviewer_user_id,
                sender_user_id=current_user.id,
                content=f"POI 有新的纠错待审核：{poi.name}",
            )
        )
    db.commit()
    db.refresh(correction)
    return _to_response(correction, correction_type)


def list_my_corrections(
    db: Session,
    current_user: User,
    offset: int,
    limit: int,
) -> PoiCorrectionListResponse:
    base = select(PoiCorrection).where(PoiCorrection.submitter_user_id == current_user.id)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(
        base.order_by(PoiCorrection.created_at.desc()).offset(offset).limit(limit)
    ).all()
    if not rows:
        return PoiCorrectionListResponse(items=[], total=0, offset=offset, limit=limit)
    type_map = {
        row.id: row
        for row in db.scalars(
            select(PoiCorrectionType).where(
                PoiCorrectionType.id.in_({item.type_id for item in rows})
            )
        ).all()
    }
    items = [_to_response(row, type_map[row.type_id]) for row in rows if row.type_id in type_map]
    return PoiCorrectionListResponse(items=items, total=total, offset=offset, limit=limit)


def list_review_corrections(
    db: Session,
    current_user: User,
    offset: int,
    limit: int,
) -> PoiCorrectionListResponse:
    base = select(PoiCorrection).where(
        PoiCorrection.status == "pending",
        (PoiCorrection.reviewer_user_id == current_user.id)
        | (PoiCorrection.reviewer_user_id.is_(None)),
    )
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(
        base.order_by(PoiCorrection.created_at.desc()).offset(offset).limit(limit)
    ).all()
    if not rows:
        return PoiCorrectionListResponse(items=[], total=0, offset=offset, limit=limit)
    type_map = {
        row.id: row
        for row in db.scalars(
            select(PoiCorrectionType).where(
                PoiCorrectionType.id.in_({item.type_id for item in rows})
            )
        ).all()
    }
    items = [_to_response(row, type_map[row.type_id]) for row in rows if row.type_id in type_map]
    return PoiCorrectionListResponse(items=items, total=total, offset=offset, limit=limit)


def review_correction(
    db: Session,
    correction_id: UUID,
    action: str,
    review_comment: str | None,
    current_user: User,
) -> PoiCorrectionReviewResponse:
    correction = db.get(PoiCorrection, correction_id)
    if correction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Correction not found")
    if correction.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Correction already reviewed"
        )
    if correction.reviewer_user_id is not None and correction.reviewer_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to review this correction"
        )

    correction_type = db.get(PoiCorrectionType, correction.type_id)
    if correction_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Correction type not found"
        )

    poi = db.get(Poi, correction.poi_id)
    if poi is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="POI not found")

    correction.status = action
    correction.reviewer_user_id = current_user.id
    correction.review_comment = review_comment.strip() if review_comment else None
    correction.reviewed_at = datetime.now(UTC)

    poi_updated = False
    if action == "accepted" and correction_type.target_field in _POI_MUTABLE_FIELDS:
        if correction_type.target_field != "ticket_price":
            parsed_value = _normalize_proposed_value(correction_type, correction.proposed_value)
            correction.before_snapshot = {
                correction_type.target_field: getattr(poi, correction_type.target_field)
            }
            setattr(poi, correction_type.target_field, parsed_value)
            correction.after_snapshot = {
                correction_type.target_field: getattr(poi, correction_type.target_field)
            }
            db.add(poi)
            poi_updated = True
            db.add(correction)
            notify_correction_accepted(
                db,
                correction=correction,
                correction_type_code=correction_type.code,
                reviewer_user_id=current_user.id,
                poi_name_snapshot=correction.source_poi_name_snapshot,
            )
            db.commit()
            db.refresh(correction)
            return PoiCorrectionReviewResponse(
                correction=_to_response(correction, correction_type), poi_updated=poi_updated
            )

        before_rule_count = db.scalar(
            select(func.count())
            .select_from(PoiTicketRule)
            .where(PoiTicketRule.poi_id == poi.id, PoiTicketRule.is_active.is_(True))
        ) or 0
        correction.before_snapshot = {
            "ticket_price": poi.ticket_price,
            "ticket_rule_count": before_rule_count,
        }

        parsed_rules = _parse_ticket_rules(correction.proposed_value)
        if parsed_rules:
            audience_codes = {str(row["audience_code"]) for row in parsed_rules}
            valid_codes = set(
                db.scalars(
                    select(PricingAudience.code).where(
                        PricingAudience.code.in_(audience_codes),
                        PricingAudience.is_active.is_(True),
                    )
                ).all()
            )
            if valid_codes != audience_codes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Correction payload contains invalid audience_code",
                )

            for existing in db.scalars(select(PoiTicketRule).where(PoiTicketRule.poi_id == poi.id)).all():
                db.delete(existing)

            min_price: float | None = None
            for row in parsed_rules:
                price = float(row["price"])
                conditions_value = row["conditions"]
                if min_price is None or price < min_price:
                    min_price = price
                db.add(
                    PoiTicketRule(
                        poi_id=poi.id,
                        audience_code=str(row["audience_code"]),
                        ticket_type=str(row["ticket_type"]),
                        time_slot=str(row["time_slot"]),
                        price=price,
                        currency=str(row["currency"]),
                        conditions=str(conditions_value) if conditions_value is not None else None,
                        source="correction",
                        is_active=True,
                    )
                )
            poi.ticket_price = min_price
        else:
            parsed_value = _normalize_proposed_value(correction_type, correction.proposed_value)
            setattr(poi, correction_type.target_field, parsed_value)

        after_rule_count = db.scalar(
            select(func.count())
            .select_from(PoiTicketRule)
            .where(PoiTicketRule.poi_id == poi.id, PoiTicketRule.is_active.is_(True))
        ) or 0
        correction.after_snapshot = {
            "ticket_price": poi.ticket_price,
            "ticket_rule_count": after_rule_count,
        }
        db.add(poi)
        poi_updated = True

    db.add(correction)
    if action == "accepted":
        notify_correction_accepted(
            db,
            correction=correction,
            correction_type_code=correction_type.code,
            reviewer_user_id=current_user.id,
            poi_name_snapshot=correction.source_poi_name_snapshot,
        )
    db.commit()
    db.refresh(correction)
    return PoiCorrectionReviewResponse(
        correction=_to_response(correction, correction_type), poi_updated=poi_updated
    )
