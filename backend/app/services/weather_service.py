from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from threading import Lock
from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.user import User
from app.schemas.weather import ItineraryWeatherDayResponse, ItineraryWeatherResponse
from app.services.collab_service import resolve_itinerary_access

_CACHE_TTL = timedelta(minutes=30)
_cache_lock = Lock()
_weather_cache: dict[str, tuple[datetime, list[ItineraryWeatherDayResponse]]] = {}


def _api_host_url() -> str:
    raw = get_settings().heweather_api_host.strip()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="天气服务未配置 API Host（请在和风控制台-设置中查看专属 Host）",
        )
    if raw.startswith("http://") or raw.startswith("https://"):
        return raw.rstrip("/")
    return f"https://{raw.rstrip('/')}"


def _api_key() -> str:
    key = get_settings().heweather_api_key.strip()
    if not key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="天气服务未配置 API Key",
        )
    return key


def _cache_key(destination: str, start_date: date, days: int) -> str:
    return f"{destination.strip().lower()}|{start_date.isoformat()}|{days}"


def _get_cached(cache_key: str) -> list[ItineraryWeatherDayResponse] | None:
    now = datetime.now(UTC)
    with _cache_lock:
        cached = _weather_cache.get(cache_key)
        if cached is None:
            return None
        expires_at, payload = cached
        if expires_at < now:
            _weather_cache.pop(cache_key, None)
            return None
        return payload


def _set_cached(cache_key: str, payload: list[ItineraryWeatherDayResponse]) -> None:
    with _cache_lock:
        _weather_cache[cache_key] = (datetime.now(UTC) + _CACHE_TTL, payload)


def _extract_problem_detail(payload: dict[str, Any]) -> str | None:
    error = payload.get("error")
    if not isinstance(error, dict):
        return None
    title = str(error.get("title") or "").strip()
    detail = str(error.get("detail") or "").strip()
    if title and detail:
        return f"{title}: {detail}"
    if detail:
        return detail
    if title:
        return title
    return None


def _ensure_qweather_code(payload: dict[str, Any], operation: str) -> None:
    code = str(payload.get("code", "")).strip()
    if code == "200":
        return
    if code == "404":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{operation}失败: code={code}",
        )
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"{operation}失败: code={code or 'unknown'}",
    )


def _request_json(
    client: httpx.Client,
    url: str,
    params: dict[str, Any],
    operation: str,
) -> dict[str, Any]:
    query = dict(params)
    query["key"] = _api_key()
    response = client.get(url, params=query)
    if response.status_code >= 400:
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        problem = _extract_problem_detail(payload)
        if problem:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"{operation}失败: {problem}",
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{operation}失败: HTTP {response.status_code}",
        )

    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{operation}失败: 响应不是有效 JSON",
        ) from exc


def _lookup_location_id(client: httpx.Client, destination: str) -> str:
    payload = _request_json(
        client,
        f"{_api_host_url()}/geo/v2/city/lookup",
        {"location": destination, "range": "cn", "number": 1, "lang": "zh"},
        "天气地理查询",
    )
    _ensure_qweather_code(payload, "天气地理查询")
    locations = payload.get("location", [])
    if not isinstance(locations, list) or not locations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到可用天气城市",
        )
    location_id = str(locations[0].get("id", "")).strip()
    if not location_id:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="天气地理查询返回异常",
        )
    return location_id


def _fetch_7d_weather(client: httpx.Client, location_id: str) -> list[dict[str, Any]]:
    payload = _request_json(
        client,
        f"{_api_host_url()}/v7/weather/7d",
        {"location": location_id, "lang": "zh"},
        "天气预报查询",
    )
    _ensure_qweather_code(payload, "天气预报查询")
    daily = payload.get("daily", [])
    if not isinstance(daily, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="天气预报返回异常",
        )
    return daily


def _to_weather_rows(
    start_date: date,
    days: int,
    daily_forecast: list[dict[str, Any]],
) -> list[ItineraryWeatherDayResponse]:
    forecast_by_date: dict[date, dict[str, Any]] = {}
    for day in daily_forecast:
        raw_date = day.get("fxDate")
        if not isinstance(raw_date, str):
            continue
        try:
            item_date = date.fromisoformat(raw_date)
        except ValueError:
            continue
        forecast_by_date[item_date] = day

    rows: list[ItineraryWeatherDayResponse] = []
    for idx in range(1, days + 1):
        target_date = start_date + timedelta(days=idx - 1)
        weather = forecast_by_date.get(target_date, {})
        temp_min = weather.get("tempMin")
        temp_max = weather.get("tempMax")
        rows.append(
            ItineraryWeatherDayResponse(
                day_index=idx,
                date=target_date,
                text=str(weather.get("textDay") or "暂无预报"),
                icon=str(weather.get("iconDay") or "999"),
                temp_min=int(temp_min) if str(temp_min).lstrip("-").isdigit() else None,
                temp_max=int(temp_max) if str(temp_max).lstrip("-").isdigit() else None,
            )
        )
    return rows


def get_itinerary_weather(
    db: Session,
    itinerary_id: UUID,
    current_user: User,
    *,
    collab_grant: str | None = None,
    force_refresh: bool = False,
) -> ItineraryWeatherResponse:
    itinerary = resolve_itinerary_access(
        db,
        itinerary_id,
        current_user,
        collab_grant=collab_grant,
        require_edit=False,
    ).itinerary
    if itinerary.start_date is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请先设置行程开始日期")

    destination = itinerary.destination.strip()
    if not destination:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="行程目的地为空")

    key = _cache_key(destination, itinerary.start_date, itinerary.days)
    if not force_refresh:
        cached = _get_cached(key)
        if cached is not None:
            return ItineraryWeatherResponse(
                itinerary_id=itinerary.id,
                start_date=itinerary.start_date,
                items=cached,
            )

    timeout = get_settings().heweather_timeout_seconds
    try:
        with httpx.Client(timeout=timeout) as client:
            location_id = _lookup_location_id(client, destination)
            daily = _fetch_7d_weather(client, location_id)
    except HTTPException:
        raise
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="天气服务请求失败",
        ) from exc

    rows = _to_weather_rows(itinerary.start_date, itinerary.days, daily)
    _set_cached(key, rows)
    return ItineraryWeatherResponse(
        itinerary_id=itinerary.id,
        start_date=itinerary.start_date,
        items=rows,
    )
