import json
import os
import random
import string
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.models.itinerary import Itinerary
from app.models.itinerary_collab import (
    ItineraryCollabDocument,
    ItineraryCollabEventLog,
    ItineraryCollabLink,
    ItineraryCollabSession,
)
from app.models.itinerary_diff_action import ItineraryDiffAction
from app.models.itinerary_fork import ItineraryFork
from app.models.itinerary_item import ItineraryItem
from app.models.itinerary_snapshot import ItinerarySnapshot
from app.models.itinerary_visit_log import ItineraryVisitLog
from app.models.passport import UserBadge, UserContribution
from app.models.poi import Poi
from app.models.poi_correction import PoiCorrection
from app.models.poi_correction_notification import PoiCorrectionNotification
from app.models.poi_ticket_rule import PoiTicketRule
from app.models.user import User
from app.models.user_notification import UserNotification
from app.models.verification_code import VerificationCode
from app.security.hashers import build_phone_lookup_hash

BASE_URL = os.getenv("ATLAS_E2E_BASE_URL", "http://localhost:8000/api/v1")
TIMEOUT_SECONDS = float(os.getenv("ATLAS_E2E_TIMEOUT_SECONDS", "20"))


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def random_suffix(n: int = 6) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(n))


def random_phone() -> str:
    return f"15{random.randint(100000000, 999999999)}"


def normalize_uuid(value: str | UUID) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


@dataclass
class SessionUser:
    phone: str
    nickname: str
    user_id: UUID
    token: str


@dataclass
class RunArtifacts:
    users: list[UUID] = field(default_factory=list)
    itineraries: list[UUID] = field(default_factory=list)
    pois: list[UUID] = field(default_factory=list)
    corrections: list[UUID] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)


@dataclass
class CheckResult:
    ok: bool
    detail: str


@dataclass
class Phase31Report:
    run_id: str
    started_at: str
    finished_at: str | None = None
    status: str = "running"
    checks: dict[str, CheckResult] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)
    created: RunArtifacts = field(default_factory=RunArtifacts)
    cleanup_deleted: dict[str, int] = field(default_factory=dict)
    cleanup_failed_items: list[str] = field(default_factory=list)
    error: str | None = None

    def set_check(self, name: str, ok: bool, detail: str) -> None:
        self.checks[name] = CheckResult(ok=ok, detail=detail)

    def as_json(self) -> str:
        data = asdict(self)
        data["checks"] = {k: asdict(v) for k, v in self.checks.items()}
        return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def assert_json(resp: httpx.Response, expected: int, action: str) -> dict[str, Any]:
    if resp.status_code != expected:
        raise RuntimeError(
            f"{action} failed: expected {expected}, got {resp.status_code}, body={resp.text[:400]}"
        )
    content_type = (resp.headers.get("content-type") or "").lower()
    if "application/json" not in content_type:
        raise RuntimeError(f"{action} failed: non-json response: {resp.text[:200]}")
    return resp.json()


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login_user(client: httpx.Client, run_id: str, role_name: str, artifacts: RunArtifacts) -> SessionUser:
    phone = random_phone()
    nickname = f"{run_id}-{role_name}-{random_suffix(4)}"

    send_resp = client.post(f"{BASE_URL}/auth/send-code", json={"phone": phone})
    send_data = assert_json(send_resp, 200, f"{role_name}: send_code")
    code = send_data.get("debug_code")
    if not isinstance(code, str) or not code:
        raise RuntimeError(
            f"{role_name}: debug_code missing, ensure app_env=dev for test environment"
        )

    login_resp = client.post(
        f"{BASE_URL}/auth/login",
        json={"phone": phone, "code": code, "nickname": nickname},
    )
    login_data = assert_json(login_resp, 200, f"{role_name}: login")
    token = login_data.get("access_token")
    user_id = login_data.get("user", {}).get("id")
    if not token or not user_id:
        raise RuntimeError(f"{role_name}: login response missing token or user id")

    parsed_user_id = normalize_uuid(user_id)
    artifacts.users.append(parsed_user_id)
    artifacts.phones.append(phone)
    return SessionUser(phone=phone, nickname=nickname, user_id=parsed_user_id, token=str(token))


def create_poi(client: httpx.Client, run_id: str, artifacts: RunArtifacts) -> UUID:
    lat = 39.90 + random.random() / 50
    lng = 116.39 + random.random() / 50
    payload = {
        "name": f"[P31-E2E:{run_id}] poi-{random_suffix(5)}",
        "type": "sightseeing",
        "longitude": lng,
        "latitude": lat,
        "address": f"{run_id}-addr-{random_suffix(4)}",
        "opening_hours": "09:00-18:00",
        "ticket_price": round(20 + random.random() * 40, 2),
    }
    resp = client.post(f"{BASE_URL}/pois", json=payload)
    data = assert_json(resp, 201, "create_poi")
    poi_id = normalize_uuid(data["id"])
    artifacts.pois.append(poi_id)
    return poi_id


def create_published_itinerary(
    client: httpx.Client,
    run_id: str,
    owner: SessionUser,
    artifacts: RunArtifacts,
) -> UUID:
    payload = {
        "title": f"[P31-E2E:{run_id}] itinerary-{random_suffix(5)}",
        "destination": "beijing",
        "days": 2,
        "status": "published",
        "visibility": "public",
        "cover_image_url": None,
    }
    resp = client.post(f"{BASE_URL}/itineraries", json=payload, headers=auth_headers(owner.token))
    data = assert_json(resp, 201, "create_itinerary")
    itinerary_id = normalize_uuid(data["id"])
    artifacts.itineraries.append(itinerary_id)
    return itinerary_id


def add_item(
    client: httpx.Client,
    itinerary_id: UUID,
    poi_id: UUID,
    token: str,
) -> UUID:
    payload = {
        "day_index": 1,
        "sort_order": 1,
        "poi_id": str(poi_id),
        "start_time": "09:00:00",
        "duration_minutes": 90,
        "cost": 35.5,
        "tips": "phase31-e2e-item",
    }
    resp = client.post(
        f"{BASE_URL}/itineraries/{itinerary_id}/items",
        json=payload,
        headers=auth_headers(token),
    )
    data = assert_json(resp, 201, "create_itinerary_item")
    return normalize_uuid(data["id"])


def fork_public_itinerary(client: httpx.Client, itinerary_id: UUID, token: str, artifacts: RunArtifacts) -> UUID:
    resp = client.post(
        f"{BASE_URL}/explore/itineraries/{itinerary_id}/fork",
        headers=auth_headers(token),
    )
    data = assert_json(resp, 201, "fork_public_itinerary")
    fork_id = normalize_uuid(data["new_itinerary_id"])
    artifacts.itineraries.append(fork_id)
    return fork_id


def pick_correction_type(client: httpx.Client) -> dict[str, Any]:
    resp = client.get(f"{BASE_URL}/corrections/types")
    data = assert_json(resp, 200, "list_correction_types")
    items = data.get("items") or []
    if not items:
        raise RuntimeError("no correction types found")

    for code in ("ticket_price_changed", "opening_hours_changed", "address_changed"):
        matched = next((item for item in items if item.get("code") == code), None)
        if matched:
            return matched
    return items[0]


def build_proposed_value(correction_type: dict[str, Any]) -> str:
    code = str(correction_type.get("code") or "")
    target_field = str(correction_type.get("target_field") or "")
    value_kind = str(correction_type.get("value_kind") or "")

    if code == "ticket_price_changed" or target_field == "ticket_price":
        return json.dumps(
            [
                {
                    "audience_code": "adult",
                    "ticket_type": "standard",
                    "time_slot": "all_day",
                    "price": 88.0,
                    "currency": "CNY",
                }
            ],
            ensure_ascii=False,
        )
    if code == "opening_hours_changed" or target_field == "opening_hours":
        return "08:30-18:30"
    if value_kind == "number":
        return "99"
    return "phase31-e2e-update"


def submit_and_accept_correction(
    client: httpx.Client,
    poi_id: UUID,
    fork_itinerary_id: UUID,
    submitter: SessionUser,
    reviewer: SessionUser,
    correction_type: dict[str, Any],
    artifacts: RunArtifacts,
) -> UUID:
    type_code = str(correction_type.get("code"))
    proposed_value = build_proposed_value(correction_type)
    submit_resp = client.post(
        f"{BASE_URL}/corrections/pois/{poi_id}",
        headers=auth_headers(submitter.token),
        data={
            "type_code": type_code,
            "proposed_value": proposed_value,
            "details": "phase31-e2e-correction",
            "source_itinerary_id": str(fork_itinerary_id),
        },
    )
    submit_data = assert_json(submit_resp, 200, "submit_correction")
    correction_id = normalize_uuid(submit_data["id"])
    artifacts.corrections.append(correction_id)

    review_resp = client.post(
        f"{BASE_URL}/corrections/{correction_id}/review",
        headers=auth_headers(reviewer.token),
        json={"action": "accepted", "review_comment": "phase31-e2e-accepted"},
    )
    assert_json(review_resp, 200, "accept_correction")
    return correction_id


def run_phase31_flow(report: Phase31Report) -> None:
    with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
        creator = login_user(client, report.run_id, "creator", report.created)
        consumer = login_user(client, report.run_id, "consumer", report.created)
        report.set_check(
            "auth",
            True,
            f"users={len(report.created.users)} creator={creator.user_id} consumer={consumer.user_id}",
        )

        poi_id = create_poi(client, report.run_id, report.created)
        source_itinerary_id = create_published_itinerary(client, report.run_id, creator, report.created)
        add_item(client, source_itinerary_id, poi_id, creator.token)
        fork_itinerary_id = fork_public_itinerary(client, source_itinerary_id, consumer.token, report.created)

        correction_type = pick_correction_type(client)
        submit_and_accept_correction(
            client,
            poi_id=poi_id,
            fork_itinerary_id=fork_itinerary_id,
            submitter=consumer,
            reviewer=creator,
            correction_type=correction_type,
            artifacts=report.created,
        )

        heatmap_resp = client.get(f"{BASE_URL}/explore/heatmap?limit=20")
        heatmap_data = assert_json(heatmap_resp, 200, "explore_heatmap")
        heat_items = heatmap_data.get("items", [])
        if not isinstance(heat_items, list):
            raise RuntimeError("explore_heatmap invalid items structure")
        if len(heat_items) > 1:
            scores = [float(item.get("heat_score", 0)) for item in heat_items]
            if scores != sorted(scores, reverse=True):
                raise RuntimeError("explore_heatmap scores are not sorted desc")
        report.set_check("heatmap", True, f"items={len(heat_items)}")

        explore_list_resp = client.get(f"{BASE_URL}/explore/itineraries?offset=0&limit=50")
        explore_list_data = assert_json(explore_list_resp, 200, "explore_itineraries")
        itineraries = explore_list_data.get("items", [])
        if not isinstance(itineraries, list):
            raise RuntimeError("explore_itineraries invalid items")
        source_row = next((row for row in itineraries if row.get("id") == str(source_itinerary_id)), None)
        if source_row is None:
            raise RuntimeError("created source itinerary missing in explore list")
        forked_count = int(source_row.get("forked_count") or 0)
        if forked_count < 1:
            raise RuntimeError(f"expected forked_count >= 1, got {forked_count}")
        report.set_check("trend", True, f"source_forked_count={forked_count}")

        reco_resp = client.get(
            f"{BASE_URL}/explore/recommendations?limit=12",
            headers=auth_headers(consumer.token),
        )
        reco_data = assert_json(reco_resp, 200, "explore_recommendations")
        reco_items = reco_data.get("items", [])
        if not isinstance(reco_items, list):
            raise RuntimeError("explore_recommendations invalid items")
        if not reco_items:
            raise RuntimeError("explore_recommendations returned empty items")
        first = reco_items[0]
        if "score" not in first or "reasons" not in first or "itinerary" not in first:
            raise RuntimeError("explore_recommendations item missing required fields")
        report.set_check("recommendations", True, f"items={len(reco_items)}")

        view_resp = client.post(
            f"{BASE_URL}/explore/itineraries/{source_itinerary_id}/view",
            headers=auth_headers(consumer.token),
        )
        view_data = assert_json(view_resp, 201, "record_public_itinerary_view")
        view_count = int(view_data.get("view_count") or 0)
        if view_count < 1 or not view_data.get("last_viewed_at"):
            raise RuntimeError("record_public_itinerary_view invalid payload")

        refreshed_list_resp = client.get(f"{BASE_URL}/explore/itineraries?offset=0&limit=50")
        refreshed_list_data = assert_json(refreshed_list_resp, 200, "explore_itineraries_after_view")
        refreshed = next(
            (row for row in refreshed_list_data.get("items", []) if row.get("id") == str(source_itinerary_id)),
            None,
        )
        if refreshed is None or refreshed.get("last_visited_at") is None:
            raise RuntimeError("expected last_visited_at to be populated after view report")
        report.set_check(
            "visit_tag",
            True,
            f"view_count={view_count} last_visited_at={refreshed.get('last_visited_at')}",
        )

        passport_resp = client.get(f"{BASE_URL}/passports/me", headers=auth_headers(consumer.token))
        passport_data = assert_json(passport_resp, 200, "passports_me")
        required = ("total_points", "level", "badges", "recent_contributions")
        missing = [field for field in required if field not in passport_data]
        if missing:
            raise RuntimeError(f"passports_me missing fields: {missing}")
        contribution_types = {
            str(item.get("action_type"))
            for item in passport_data.get("recent_contributions", [])
            if isinstance(item, dict)
        }
        if "correction_accepted" not in contribution_types:
            raise RuntimeError("passports_me missing correction_accepted contribution")
        report.set_check(
            "passport",
            True,
            f"level={passport_data.get('level')} points={passport_data.get('total_points')}",
        )

        report.metrics = {
            "creator_user_id": str(creator.user_id),
            "consumer_user_id": str(consumer.user_id),
            "reviewer_user_id": str(creator.user_id),
            "source_itinerary_id": str(source_itinerary_id),
            "fork_itinerary_id": str(fork_itinerary_id),
            "poi_id": str(poi_id),
            "recommendations_count": len(reco_items),
            "heatmap_count": len(heat_items),
            "view_count": view_count,
        }


def cleanup_created_data(report: Phase31Report) -> None:
    deleted: dict[str, int] = {}
    failures: list[str] = []

    def run_delete(label: str, stmt) -> None:
        try:
            count = db.execute(stmt).rowcount or 0
            deleted[label] = deleted.get(label, 0) + int(count)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{label}: {exc}")

    user_ids = [uid for uid in report.created.users]
    itinerary_ids = [iid for iid in report.created.itineraries]
    poi_ids = [pid for pid in report.created.pois]
    correction_ids = [cid for cid in report.created.corrections]
    phone_hashes = [build_phone_lookup_hash(phone) for phone in report.created.phones]

    with SessionLocal() as db:
        # notifications/corrections
        if correction_ids:
            run_delete(
                "poi_correction_notifications_by_correction",
                delete(PoiCorrectionNotification).where(
                    PoiCorrectionNotification.correction_id.in_(correction_ids)
                ),
            )
            run_delete(
                "user_notifications_by_correction",
                delete(UserNotification).where(UserNotification.correction_id.in_(correction_ids)),
            )
            run_delete(
                "poi_corrections",
                delete(PoiCorrection).where(PoiCorrection.id.in_(correction_ids)),
            )

        # itinerary-related
        if itinerary_ids:
            run_delete(
                "itinerary_visit_logs_by_itinerary",
                delete(ItineraryVisitLog).where(ItineraryVisitLog.itinerary_id.in_(itinerary_ids)),
            )
            run_delete(
                "itinerary_diff_actions",
                delete(ItineraryDiffAction).where(ItineraryDiffAction.itinerary_id.in_(itinerary_ids)),
            )
            run_delete(
                "itinerary_collab_event_logs",
                delete(ItineraryCollabEventLog).where(ItineraryCollabEventLog.itinerary_id.in_(itinerary_ids)),
            )
            run_delete(
                "itinerary_collab_sessions",
                delete(ItineraryCollabSession).where(ItineraryCollabSession.itinerary_id.in_(itinerary_ids)),
            )
            run_delete(
                "itinerary_collab_links",
                delete(ItineraryCollabLink).where(ItineraryCollabLink.itinerary_id.in_(itinerary_ids)),
            )
            run_delete(
                "itinerary_collab_documents",
                delete(ItineraryCollabDocument).where(ItineraryCollabDocument.itinerary_id.in_(itinerary_ids)),
            )
            run_delete(
                "user_notifications_by_source_itinerary",
                delete(UserNotification).where(UserNotification.source_itinerary_id.in_(itinerary_ids)),
            )
            run_delete(
                "user_notifications_by_forked_itinerary",
                delete(UserNotification).where(UserNotification.forked_itinerary_id.in_(itinerary_ids)),
            )
            run_delete(
                "itinerary_forks",
                delete(ItineraryFork).where(
                    ItineraryFork.source_itinerary_id.in_(itinerary_ids)
                    | ItineraryFork.forked_itinerary_id.in_(itinerary_ids)
                ),
            )
            run_delete(
                "itinerary_items",
                delete(ItineraryItem).where(ItineraryItem.itinerary_id.in_(itinerary_ids)),
            )
            run_delete(
                "itinerary_snapshots",
                delete(ItinerarySnapshot).where(ItinerarySnapshot.itinerary_id.in_(itinerary_ids)),
            )
            run_delete(
                "itineraries",
                delete(Itinerary).where(Itinerary.id.in_(itinerary_ids)),
            )

        # poi-related
        if poi_ids:
            run_delete(
                "poi_ticket_rules",
                delete(PoiTicketRule).where(PoiTicketRule.poi_id.in_(poi_ids)),
            )
            run_delete(
                "pois",
                delete(Poi).where(Poi.id.in_(poi_ids)),
            )

        # user/passport/auth-related
        if user_ids:
            run_delete(
                "user_notifications_by_recipient",
                delete(UserNotification).where(UserNotification.recipient_user_id.in_(user_ids)),
            )
            run_delete(
                "user_notifications_by_sender",
                delete(UserNotification).where(UserNotification.sender_user_id.in_(user_ids)),
            )
            run_delete(
                "itinerary_visit_logs_by_viewer",
                delete(ItineraryVisitLog).where(ItineraryVisitLog.viewer_user_id.in_(user_ids)),
            )
            run_delete(
                "user_badges",
                delete(UserBadge).where(UserBadge.user_id.in_(user_ids)),
            )
            run_delete(
                "user_contributions",
                delete(UserContribution).where(UserContribution.user_id.in_(user_ids)),
            )
            run_delete(
                "users",
                delete(User).where(User.id.in_(user_ids)),
            )

        if phone_hashes:
            run_delete(
                "verification_codes",
                delete(VerificationCode).where(VerificationCode.phone_lookup_hash.in_(phone_hashes)),
            )

        if failures:
            db.rollback()
        else:
            db.commit()

    report.cleanup_deleted = deleted
    report.cleanup_failed_items = failures


def validate_service_health(report: Phase31Report) -> None:
    with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
        health = client.get(f"{BASE_URL}/health/live")
        if health.status_code != 200:
            raise RuntimeError(f"health check failed: {health.status_code} {health.text[:200]}")
        report.set_check("health", True, "api live=200")


def main() -> None:
    run_id = f"p31-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{random_suffix(6)}"
    report = Phase31Report(run_id=run_id, started_at=now_iso())

    try:
        validate_service_health(report)
        run_phase31_flow(report)
        report.status = "pass"
    except Exception as exc:  # noqa: BLE001
        report.status = "fail"
        report.error = str(exc)
    finally:
        cleanup_created_data(report)
        if report.cleanup_failed_items and report.status == "pass":
            report.status = "fail"
            report.error = "cleanup failed"
        report.finished_at = now_iso()
        print(report.as_json())
        if report.status != "pass":
            raise SystemExit(1)


if __name__ == "__main__":
    main()
