from __future__ import annotations

import os
import random
import string
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

BASE_URL = os.getenv("ATLAS_E2E_BASE_URL", "http://localhost:8000/api/v1")
TIMEOUT = float(os.getenv("ATLAS_E2E_TIMEOUT_SECONDS", "15"))


@dataclass
class SessionUser:
    phone: str
    nickname: str
    user_id: str
    token: str


def _random_phone() -> str:
    prefix = random.choice(["130", "131", "132", "155", "156", "157", "186", "187", "188"])
    suffix = "".join(random.choice(string.digits) for _ in range(8))
    return f"{prefix}{suffix}"


def _random_suffix() -> str:
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6))


def _assert_status(resp: httpx.Response, expected: int, action: str) -> dict[str, Any]:
    if resp.status_code != expected:
        raise RuntimeError(
            f"{action} failed: expected {expected}, got {resp.status_code}, body={resp.text[:300]}"
        )
    if "application/json" not in (resp.headers.get("content-type") or ""):
        raise RuntimeError(f"{action} failed: non-json response: {resp.text[:300]}")
    return resp.json()


def _login_user(client: httpx.Client, nickname_prefix: str) -> SessionUser:
    phone = _random_phone()
    nickname = f"{nickname_prefix}-{_random_suffix()}"
    send_payload = {"phone": phone}
    send_resp = client.post(f"{BASE_URL}/auth/send-code", json=send_payload)
    send_data = _assert_status(send_resp, 200, "send_code")
    code = send_data.get("debug_code")
    if not isinstance(code, str) or not code:
        raise RuntimeError("send_code failed: debug_code missing")

    login_payload = {"phone": phone, "code": code, "nickname": nickname}
    login_resp = client.post(f"{BASE_URL}/auth/login", json=login_payload)
    login_data = _assert_status(login_resp, 200, "login")
    return SessionUser(
        phone=phone,
        nickname=nickname,
        user_id=str(login_data["user"]["id"]),
        token=str(login_data["access_token"]),
    )


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_poi(client: httpx.Client) -> str:
    suffix = _random_suffix()
    payload = {
        "name": f"自动化景点-{suffix}",
        "type": "sightseeing",
        "longitude": 116.39 + random.random() / 100,
        "latitude": 39.90 + random.random() / 100,
        "address": f"自动化地址-{suffix}",
        "opening_hours": "09:00-18:00",
        "ticket_price": 50.0,
    }
    resp = client.post(f"{BASE_URL}/pois", json=payload)
    data = _assert_status(resp, 201, "create_poi")
    return str(data["id"])


def _create_published_itinerary(client: httpx.Client, token: str) -> str:
    suffix = _random_suffix()
    payload = {
        "title": f"自动化源行程-{suffix}",
        "destination": "北京",
        "days": 2,
        "status": "published",
        "visibility": "public",
        "cover_image_url": None,
    }
    resp = client.post(f"{BASE_URL}/itineraries", json=payload, headers=_headers(token))
    data = _assert_status(resp, 201, "create_itinerary")
    return str(data["id"])


def _add_item(client: httpx.Client, token: str, itinerary_id: str, poi_id: str) -> None:
    payload = {
        "day_index": 1,
        "sort_order": 1,
        "poi_id": poi_id,
        "start_time": "09:00:00",
        "duration_minutes": 90,
        "cost": 30.0,
        "tips": "自动化验证",
    }
    resp = client.post(
        f"{BASE_URL}/itineraries/{itinerary_id}/items",
        json=payload,
        headers=_headers(token),
    )
    _assert_status(resp, 201, "create_itinerary_item")


def _fork(client: httpx.Client, token: str, source_itinerary_id: str) -> str:
    resp = client.post(
        f"{BASE_URL}/explore/itineraries/{source_itinerary_id}/fork",
        headers=_headers(token),
    )
    data = _assert_status(resp, 201, "fork_public_itinerary")
    return str(data["new_itinerary_id"])


def _update_source_itinerary(client: httpx.Client, token: str, itinerary_id: str) -> None:
    payload = {
        "title": f"自动化源行程更新-{datetime.now().strftime('%H%M%S')}",
        "visibility": "public",
        "status": "published",
    }
    resp = client.put(
        f"{BASE_URL}/itineraries/{itinerary_id}",
        json=payload,
        headers=_headers(token),
    )
    _assert_status(resp, 200, "update_source_itinerary")


def _list_notifications(client: httpx.Client, token: str) -> dict[str, Any]:
    resp = client.get(f"{BASE_URL}/notifications?offset=0&limit=100", headers=_headers(token))
    return _assert_status(resp, 200, "list_notifications")


def _submit_correction(
    client: httpx.Client,
    token: str,
    poi_id: str,
    source_itinerary_id: str,
) -> str:
    data = {
        "type_code": "opening_hours_changed",
        "proposed_value": "10:00-19:00",
        "details": "自动化纠错验证",
        "source_itinerary_id": source_itinerary_id,
    }
    resp = client.post(
        f"{BASE_URL}/corrections/pois/{poi_id}",
        data=data,
        headers=_headers(token),
    )
    result = _assert_status(resp, 200, "submit_correction")
    return str(result["id"])


def _accept_correction(client: httpx.Client, token: str, correction_id: str) -> None:
    payload = {"action": "accepted", "review_comment": "自动化通过"}
    resp = client.post(
        f"{BASE_URL}/corrections/{correction_id}/review",
        json=payload,
        headers=_headers(token),
    )
    _assert_status(resp, 200, "accept_correction")


def _mark_read(client: httpx.Client, token: str, notification_id: str) -> None:
    resp = client.post(
        f"{BASE_URL}/notifications/{notification_id}/read",
        json={"read": True},
        headers=_headers(token),
    )
    _assert_status(resp, 200, "mark_notification_read")


def _mark_all_read(client: httpx.Client, token: str) -> int:
    resp = client.post(f"{BASE_URL}/notifications/read-all", headers=_headers(token))
    data = _assert_status(resp, 200, "mark_all_notifications_read")
    return int(data["updated_count"])


def run() -> None:
    with httpx.Client(timeout=TIMEOUT) as client:
        owner = _login_user(client, "owner")
        fork_a = _login_user(client, "forkA")
        fork_b = _login_user(client, "forkB")

        poi_id = _create_poi(client)
        source_itinerary_id = _create_published_itinerary(client, owner.token)
        _add_item(client, owner.token, source_itinerary_id, poi_id)

        fork_a_itinerary_id = _fork(client, fork_a.token, source_itinerary_id)
        _fork(client, fork_b.token, source_itinerary_id)
        if not fork_a_itinerary_id:
            raise RuntimeError("fork failed: missing itinerary id")

        _update_source_itinerary(client, owner.token, source_itinerary_id)
        fork_a_notifications = _list_notifications(client, fork_a.token)
        source_update_events = [
            row
            for row in fork_a_notifications["items"]
            if row["event_type"] == "source_itinerary_updated"
        ]
        if not source_update_events:
            raise RuntimeError("expected source_itinerary_updated notification for forkA")

        correction_id = _submit_correction(client, fork_a.token, poi_id, fork_a_itinerary_id)
        _accept_correction(client, owner.token, correction_id)

        fork_a_after = _list_notifications(client, fork_a.token)
        fork_b_after = _list_notifications(client, fork_b.token)
        if not any(row["event_type"] == "correction_accepted" for row in fork_a_after["items"]):
            raise RuntimeError("expected correction_accepted notification for submitter forkA")
        if not any(row["event_type"] == "correction_accepted" for row in fork_b_after["items"]):
            raise RuntimeError("expected correction_accepted notification for related forkB")

        first_unread = next((row for row in fork_a_after["items"] if not row["is_read"]), None)
        if first_unread is None:
            raise RuntimeError("expected at least one unread notification for forkA")
        _mark_read(client, fork_a.token, str(first_unread["id"]))
        updated = _mark_all_read(client, fork_b.token)
        if updated < 1:
            raise RuntimeError("expected mark_all_read to update at least one notification for forkB")

        print("PASS: Phase 2.4 notification e2e verification succeeded.")
        print(f"owner={owner.user_id} forkA={fork_a.user_id} forkB={fork_b.user_id} poi={poi_id}")


if __name__ == "__main__":
    run()
