from __future__ import annotations

from collections import defaultdict
from datetime import datetime, time
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from pydantic import BaseModel, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.itinerary import Itinerary
from app.models.itinerary_item import ItineraryItem
from app.models.poi import Poi
from app.models.user import User
from app.schemas.ai_engine import (
    AiImportRequest,
    AiImportResponse,
    AiPreviewItem,
    AiPreviewPoi,
    AiPreviewRequest,
    AiPreviewResponse,
)

settings = get_settings()


class _AiRawItem(BaseModel):
    day_index: int
    name: str
    type: str | None = "scenic"
    start_time: str | None = None
    duration_minutes: int | None = None
    cost: float | None = None
    tips: str | None = None


class _AiRawResponse(BaseModel):
    title: str
    destination: str
    days: int
    items: list[_AiRawItem]


def _normalize_text(value: str) -> str:
    return "".join(value.lower().split())


def _place_has_grounding(place_name: str, raw_text: str) -> bool:
    normalized_name = _normalize_text(place_name)
    normalized_raw = _normalize_text(raw_text)
    if not normalized_name:
        return False
    if normalized_name in normalized_raw:
        return True
    # If full name is not found, allow partial grounding with meaningful chunks.
    chunks = [normalized_name[i : i + 2] for i in range(0, max(len(normalized_name) - 1, 1))]
    strong_chunks = [chunk for chunk in chunks if len(chunk) >= 2]
    if not strong_chunks:
        return False
    hit_count = sum(1 for chunk in strong_chunks if chunk in normalized_raw)
    return hit_count >= 2


def _raise_ai_preview_422(
    error_code: str,
    reason: str,
    raw_text: str,
    suggested_actions: list[str] | None = None,
) -> None:
    excerpt = raw_text.strip().replace("\n", " ")
    if len(excerpt) > 120:
        excerpt = f"{excerpt[:120]}..."
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail={
            "error_code": error_code,
            "reason": reason,
            "raw_excerpt": excerpt or None,
            "suggested_actions": suggested_actions
            or ["请补充更明确的地点与天次描述后重试", "或跳过 AI 生成，直接手动编辑时间轴"],
        },
    )


def _parse_point_text(value: str) -> tuple[float, float]:
    raw = value.strip().removeprefix("POINT(").removesuffix(")")
    lon_str, lat_str = raw.split(" ", maxsplit=1)
    return float(lon_str), float(lat_str)


def _point_text(longitude: float, latitude: float) -> str:
    return f"POINT({longitude} {latitude})"


def _parse_time(value: str | None) -> time | None:
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(trimmed, fmt).time()
        except ValueError:
            continue
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid time format: {value}",
    )


def _ensure_owned_itinerary(db: Session, itinerary_id: UUID, current_user: User) -> Itinerary:
    itinerary = db.get(Itinerary, itinerary_id)
    if itinerary is None or itinerary.creator_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    return itinerary


def _call_deepseek(raw_text: str) -> _AiRawResponse:
    if not settings.deepseek_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DeepSeek API key is not configured",
        )

    system_prompt = (
        "你是旅行行程结构化助手。"
        "请把用户输入转换为 JSON 对象，且只输出 JSON。"
        "JSON 结构必须包含 title、destination、days、items。"
        "items 是数组，每个元素必须包含 day_index、name，"
        "可选 type/start_time/duration_minutes/cost/tips。"
        "day_index 从 1 开始。"
    )
    payload = {
        "model": settings.deepseek_model,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": raw_text},
        ],
    }
    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json; charset=utf-8",
    }

    try:
        with httpx.Client(timeout=45.0) as client:
            response = client.post(
                f"{settings.deepseek_base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"DeepSeek request failed: {exc.__class__.__name__}",
        ) from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"DeepSeek request failed with status {response.status_code}",
        )

    data = response.json()
    content = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("content")
    )
    if not isinstance(content, str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="DeepSeek response content is invalid",
        )

    try:
        return _AiRawResponse.model_validate_json(content)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"DeepSeek JSON schema validation failed: {exc.errors()[0]['msg']}",
        ) from exc


def _call_gemini(raw_text: str) -> _AiRawResponse:
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini API key is not configured",
        )

    prompt = f"""
你是旅行时间轴结构化助手。你的任务是把用户的游记/备忘录规范化为“时间块”JSON。
必须只输出 JSON，不要输出任何解释文本。

输出结构（字段名必须完全一致）：
{{
  "title": "行程标题",
  "destination": "目的地",
  "days": 1,
  "items": [
    {{
      "day_index": 1,
      "name": "景点或地点名称",
      "type": "scenic",
      "start_time": "09:30",
      "duration_minutes": 120,
      "cost": 0,
      "tips": "可选提示"
    }}
  ]
}}

规范化规则：
1) day_index 从 1 开始；缺失时按叙述顺序推断，无法推断则默认为 1。
2) name 必须有值，禁止空字符串。
3) start_time 无法确定时填 null；若有值使用 HH:MM 格式。
4) duration_minutes/cost/tips/type 无法确定时可填 null。
5) items 至少输出 1 条；如果文本极短，也要抽取最核心的一个地点。
6) 不要编造不存在的天次与预算；不确定就填 null 或默认 day_index=1。

用户输入：
{raw_text}
"""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
        },
    }

    endpoint = (
        f"{settings.gemini_base_url.rstrip('/')}/v1beta/models/"
        f"{settings.gemini_model}:generateContent"
    )
    try:
        with httpx.Client(timeout=45.0) as client:
            response = client.post(
                endpoint,
                params={"key": settings.gemini_api_key},
                headers={"Content-Type": "application/json; charset=utf-8"},
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini request failed: {exc.__class__.__name__}",
        ) from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini request failed with status {response.status_code}",
        )

    data = response.json()
    candidates = data.get("candidates", [])
    if not isinstance(candidates, list) or not candidates:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Gemini response content is invalid",
        )
    parts = candidates[0].get("content", {}).get("parts", [])
    if not isinstance(parts, list) or not parts or not isinstance(parts[0].get("text"), str):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Gemini response content is invalid",
        )
    content = parts[0]["text"]

    try:
        return _AiRawResponse.model_validate_json(content)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Gemini JSON schema validation failed: {exc.errors()[0]['msg']}",
        ) from exc


def _call_llm(raw_text: str) -> _AiRawResponse:
    provider = settings.ai_provider.strip().lower()
    if provider == "deepseek":
        return _call_deepseek(raw_text)
    if provider == "gemini":
        return _call_gemini(raw_text)
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"Unsupported AI provider: {settings.ai_provider}",
    )


def _validate_ai_raw_response(raw: _AiRawResponse, raw_text: str) -> None:
    if not raw.items:
        _raise_ai_preview_422(
            error_code="AI_EMPTY_ITEMS",
            reason="AI 未抽取到可用时间块，请补充地点或天次信息后重试。",
            raw_text=raw_text,
        )
    for idx, item in enumerate(raw.items, start=1):
        if item.day_index < 1:
            _raise_ai_preview_422(
                error_code="AI_INVALID_DAY_INDEX",
                reason=f"第 {idx} 个时间块的 day_index 小于 1。",
                raw_text=raw_text,
            )
        if not item.name or not item.name.strip():
            _raise_ai_preview_422(
                error_code="AI_EMPTY_NAME",
                reason=f"第 {idx} 个时间块缺少地点名称。",
                raw_text=raw_text,
            )
    grounded_count = sum(1 for item in raw.items if _place_has_grounding(item.name, raw_text))
    if grounded_count == 0:
        _raise_ai_preview_422(
            error_code="AI_UNGROUNDED_ITEMS",
            reason="AI 生成的地点与原文缺乏可验证关联，请补充明确地点后重试。",
            raw_text=raw_text,
        )


def _resolve_local_poi(db: Session, name: str) -> AiPreviewPoi | None:
    stmt = (
        select(Poi, func.ST_AsText(Poi.geom))
        .where(func.lower(Poi.name) == name.lower())
        .order_by(Poi.updated_at.desc())
        .limit(1)
    )
    row = db.execute(stmt).one_or_none()
    if row is None:
        return None
    poi, wkt = row
    longitude, latitude = _parse_point_text(wkt)
    return AiPreviewPoi(
        poi_id=poi.id,
        name=poi.name,
        type=poi.type,
        longitude=longitude,
        latitude=latitude,
        address=poi.address,
        opening_hours=poi.opening_hours,
        ticket_price=float(poi.ticket_price) if poi.ticket_price is not None else None,
        match_source="local",
    )


def _resolve_amap_poi(name: str, destination: str, fallback_type: str) -> AiPreviewPoi:
    if not settings.amap_web_service_key:
        return AiPreviewPoi(name=name, type=fallback_type, match_source="unresolved")

    params = {
        "key": settings.amap_web_service_key,
        "keywords": name,
        "city": destination,
        "offset": 1,
        "page": 1,
        "extensions": "base",
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get("https://restapi.amap.com/v3/place/text", params=params)
    except httpx.HTTPError:
        return AiPreviewPoi(name=name, type=fallback_type, match_source="unresolved")

    if response.status_code >= 400:
        return AiPreviewPoi(name=name, type=fallback_type, match_source="unresolved")

    data = response.json()
    pois = data.get("pois")
    if not isinstance(pois, list) or not pois:
        return AiPreviewPoi(name=name, type=fallback_type, match_source="unresolved")

    first = pois[0]
    location = first.get("location", "")
    parts = location.split(",")
    if len(parts) != 2:
        return AiPreviewPoi(name=name, type=fallback_type, match_source="unresolved")
    try:
        longitude = float(parts[0])
        latitude = float(parts[1])
    except ValueError:
        return AiPreviewPoi(name=name, type=fallback_type, match_source="unresolved")

    return AiPreviewPoi(
        name=first.get("name") or name,
        type=fallback_type,
        longitude=longitude,
        latitude=latitude,
        address=first.get("address") or None,
        opening_hours=None,
        ticket_price=None,
        match_source="amap",
    )


def preview_ai_plan(
    db: Session, payload: AiPreviewRequest, current_user: User
) -> AiPreviewResponse:
    _ensure_owned_itinerary(db, payload.itinerary_id, current_user)
    raw = _call_llm(payload.raw_text)
    _validate_ai_raw_response(raw, payload.raw_text)
    grouped_items: dict[int, list[AiPreviewItem]] = defaultdict(list)

    for source_item in raw.items:
        fallback_type = source_item.type or "scenic"
        local = _resolve_local_poi(db, source_item.name)
        poi = local if local else _resolve_amap_poi(
            source_item.name, raw.destination, fallback_type
        )
        grouped_items[source_item.day_index].append(
            AiPreviewItem(
                day_index=source_item.day_index,
                sort_order=1,
                start_time=source_item.start_time,
                duration_minutes=source_item.duration_minutes,
                cost=source_item.cost,
                tips=source_item.tips,
                poi=poi,
            )
        )

    items: list[AiPreviewItem] = []
    for day in sorted(grouped_items.keys()):
        for index, item in enumerate(grouped_items[day], start=1):
            item.sort_order = index
            items.append(item)

    days = max(raw.days, 1)
    if items:
        days = max(days, max(item.day_index for item in items))

    return AiPreviewResponse(
        title=raw.title,
        destination=raw.destination,
        days=days,
        items=items,
    )


def _resolve_or_create_poi(db: Session, poi: AiPreviewPoi) -> UUID:
    if poi.poi_id:
        existing = db.get(Poi, poi.poi_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"POI not found: {poi.poi_id}",
            )
        return existing.id

    if poi.match_source == "unresolved" or poi.longitude is None or poi.latitude is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unresolved POI: {poi.name}",
        )

    new_poi = Poi(
        name=poi.name,
        type=poi.type,
        geom=_point_text(poi.longitude, poi.latitude),
        address=poi.address,
        opening_hours=poi.opening_hours,
        ticket_price=poi.ticket_price,
        parent_poi_id=None,
    )
    db.add(new_poi)
    db.flush()
    return new_poi.id


def import_ai_plan(db: Session, payload: AiImportRequest, current_user: User) -> AiImportResponse:
    itinerary = _ensure_owned_itinerary(db, payload.itinerary_id, current_user)

    stmt = (
        select(ItineraryItem.day_index, func.max(ItineraryItem.sort_order))
        .where(ItineraryItem.itinerary_id == itinerary.id)
        .group_by(ItineraryItem.day_index)
    )
    day_order_rows = db.execute(stmt).all()
    max_sort_by_day = {day_index: max_order for day_index, max_order in day_order_rows}

    imported_count = 0
    ordered_items = sorted(
        payload.preview.items, key=lambda item: (item.day_index, item.sort_order)
    )
    for item in ordered_items:
        if item.day_index > itinerary.days:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"day_index out of itinerary range: {item.day_index}",
            )
        poi_id = _resolve_or_create_poi(db, item.poi)
        sort_order = int(max_sort_by_day.get(item.day_index, 0)) + 1
        max_sort_by_day[item.day_index] = sort_order
        db.add(
            ItineraryItem(
                itinerary_id=itinerary.id,
                day_index=item.day_index,
                sort_order=sort_order,
                poi_id=poi_id,
                start_time=_parse_time(item.start_time),
                duration_minutes=item.duration_minutes,
                cost=item.cost,
                tips=item.tips,
            )
        )
        imported_count += 1

    if imported_count > 0 and itinerary.status == "draft":
        itinerary.status = "in_progress"
        db.add(itinerary)

    db.commit()
    return AiImportResponse(imported_count=imported_count)
