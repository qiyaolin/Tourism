import asyncio
import base64
import contextlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import redis.asyncio as redis
from fastapi import WebSocket
from redis.exceptions import RedisError

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.itinerary_collab import ItineraryCollabDocument, ItineraryCollabEventLog
from app.schemas.itinerary_collab import ItineraryCollabParticipant
from app.services.collab_service import CollabIdentity

_PENDING_ROOMS_KEY = "atlas:collab:pending:rooms"
_PENDING_LIST_PREFIX = "atlas:collab:pending:"
logger = logging.getLogger(__name__)


@dataclass
class RuntimeConnection:
    connection_id: str
    session_id: UUID
    itinerary_id: UUID
    websocket: WebSocket
    identity: CollabIdentity
    joined_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    cursor: dict | None = None


class CollabRuntime:
    def __init__(self) -> None:
        self._redis: redis.Redis | None = None
        self._connections: dict[UUID, dict[str, RuntimeConnection]] = {}
        self._lock = asyncio.Lock()
        self._flush_task: asyncio.Task | None = None
        self._running = False

    async def startup(self) -> None:
        if self._running:
            return
        settings = get_settings()
        self._redis = redis.from_url(settings.collab_redis_url, decode_responses=False)
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop(), name="collab-flush-loop")

    async def shutdown(self) -> None:
        self._running = False
        if self._flush_task is not None:
            self._flush_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._flush_task
            self._flush_task = None
        if self._redis is not None:
            await self._redis.close()
            self._redis = None

    async def register(
        self,
        *,
        itinerary_id: UUID,
        websocket: WebSocket,
        identity: CollabIdentity,
        session_id: UUID,
    ) -> RuntimeConnection:
        conn = RuntimeConnection(
            connection_id=uuid.uuid4().hex,
            session_id=session_id,
            itinerary_id=itinerary_id,
            websocket=websocket,
            identity=identity,
        )
        async with self._lock:
            room = self._connections.setdefault(itinerary_id, {})
            room[conn.connection_id] = conn
        await self._send_join_payload(conn)
        await self._broadcast_presence(itinerary_id)
        return conn

    async def unregister(self, conn: RuntimeConnection) -> None:
        async with self._lock:
            room = self._connections.get(conn.itinerary_id)
            if room is not None:
                room.pop(conn.connection_id, None)
                if not room:
                    self._connections.pop(conn.itinerary_id, None)
        await self._broadcast_presence(conn.itinerary_id)

    async def broadcast_cursor(self, conn: RuntimeConnection, cursor: dict[str, Any]) -> None:
        conn.cursor = cursor
        await self._broadcast_presence(conn.itinerary_id)

    async def broadcast_update(
        self, conn: RuntimeConnection, update_b64: str, event_meta: dict[str, Any]
    ) -> None:
        message = {
            "type": "collab:update",
            "session_id": conn.connection_id,
            "update_b64": update_b64,
            "meta": event_meta,
        }
        await self._broadcast(
            conn.itinerary_id,
            message,
            exclude_connection_id=conn.connection_id,
        )
        persisted = await self._persist_pending_update(conn, update_b64, event_meta)
        if not persisted:
            await self._persist_update_direct(conn, update_b64, event_meta)

    async def _send_join_payload(self, conn: RuntimeConnection) -> None:
        snapshot_b64, needs_seed = await self._load_document_snapshot(conn.itinerary_id)
        participants = self._participants(conn.itinerary_id)
        await conn.websocket.send_json(
            {
                "type": "collab:joined",
                "itinerary_id": str(conn.itinerary_id),
                "permission": conn.identity.permission,
                "participants": participants,
                "snapshot_update_b64": snapshot_b64,
                "needs_seed": needs_seed,
            }
        )

    async def _broadcast_presence(self, itinerary_id: UUID) -> None:
        await self._broadcast(
            itinerary_id,
            {
                "type": "collab:presence",
                "participants": self._participants(itinerary_id),
            },
        )

    async def _broadcast(
        self,
        itinerary_id: UUID,
        message: dict[str, Any],
        exclude_connection_id: str | None = None,
    ) -> None:
        room = list(self._connections.get(itinerary_id, {}).values())
        if not room:
            return
        for conn in room:
            if exclude_connection_id and conn.connection_id == exclude_connection_id:
                continue
            await conn.websocket.send_json(message)

    def _participants(self, itinerary_id: UUID) -> list[dict[str, Any]]:
        room = self._connections.get(itinerary_id, {})
        items = [
            ItineraryCollabParticipant(
                session_id=conn.connection_id,
                participant_type=conn.identity.participant_type,
                participant_user_id=conn.identity.actor_user_id,
                display_name=conn.identity.display_name,
                permission=conn.identity.permission,
                joined_at=conn.joined_at,
                cursor=conn.cursor,
            ).model_dump(mode="json")
            for conn in room.values()
        ]
        items.sort(key=lambda item: item["joined_at"])
        return items

    async def _persist_pending_update(
        self, conn: RuntimeConnection, update_b64: str, event_meta: dict[str, Any]
    ) -> bool:
        if self._redis is None:
            return False
        payload = {
            "session_id": conn.connection_id,
            "participant_type": conn.identity.participant_type,
            "actor_user_id": str(conn.identity.actor_user_id)
            if conn.identity.actor_user_id
            else None,
            "guest_name": conn.identity.guest_name,
            "update_b64": update_b64,
            "meta": event_meta,
            "created_at": datetime.now(UTC).isoformat(),
        }
        key = f"{_PENDING_LIST_PREFIX}{conn.itinerary_id}"
        try:
            await self._redis.sadd(_PENDING_ROOMS_KEY, str(conn.itinerary_id))
            await self._redis.rpush(key, json.dumps(payload, ensure_ascii=True).encode("utf-8"))
            return True
        except RedisError as exc:
            logger.warning(
                "collab redis unavailable; switching to direct persistence: %s",
                exc,
            )
            await self._disable_redis()
            return False

    async def _disable_redis(self) -> None:
        if self._redis is None:
            return
        with contextlib.suppress(Exception):
            await self._redis.close()
        self._redis = None

    @staticmethod
    def _resolve_origin(meta: dict[str, Any]) -> str:
        maybe_origin = meta.get("origin")
        if isinstance(maybe_origin, str) and maybe_origin.strip():
            return maybe_origin.strip()
        return "local"

    async def _persist_update_direct(
        self,
        conn: RuntimeConnection,
        update_b64: str,
        event_meta: dict[str, Any],
    ) -> None:
        try:
            update_bytes = base64.b64decode(update_b64)
        except ValueError:
            return
        origin = self._resolve_origin(event_meta)
        with SessionLocal() as db:
            doc_row = db.get(ItineraryCollabDocument, conn.itinerary_id)
            if doc_row is None:
                doc_row = ItineraryCollabDocument(
                    itinerary_id=conn.itinerary_id, state_update=None, update_count=0
                )
                db.add(doc_row)
                db.flush()

            doc_row.state_update = update_bytes
            doc_row.update_count = int(doc_row.update_count or 0) + 1
            db.add(doc_row)

            if origin not in {"bootstrap", "seed"}:
                actor_user_id = conn.identity.actor_user_id
                db.add(
                    ItineraryCollabEventLog(
                        itinerary_id=conn.itinerary_id,
                        actor_type=conn.identity.participant_type,
                        actor_user_id=actor_user_id,
                        guest_name=conn.identity.guest_name,
                        event_type="content_sync",
                        target_type="document",
                        target_id=str(conn.itinerary_id),
                        payload={
                            "bytes": len(update_bytes),
                            "updates": 1,
                            "origin_counts": {origin: 1},
                            "origin": origin,
                            "session_ids": [conn.connection_id],
                        },
                    )
                )
            db.commit()

    async def _load_document_snapshot(self, itinerary_id: UUID) -> tuple[str | None, bool]:
        with SessionLocal() as db:
            row = db.get(ItineraryCollabDocument, itinerary_id)
            if row is None or not row.state_update:
                return None, True
            return base64.b64encode(row.state_update).decode("ascii"), False

    async def _flush_loop(self) -> None:
        settings = get_settings()
        interval = max(1, settings.collab_flush_interval_seconds)
        while self._running:
            try:
                await self._flush_once()
            except Exception:
                pass
            await asyncio.sleep(interval)

    async def _flush_once(self) -> None:
        if self._redis is None:
            return
        room_ids = await self._redis.smembers(_PENDING_ROOMS_KEY)
        if not room_ids:
            return
        for raw in room_ids:
            try:
                itinerary_id = UUID(raw.decode("utf-8") if isinstance(raw, bytes) else str(raw))
            except ValueError:
                continue
            await self._flush_room(itinerary_id)

    async def _flush_room(self, itinerary_id: UUID) -> None:
        if self._redis is None:
            return
        key = f"{_PENDING_LIST_PREFIX}{itinerary_id}"
        raw_items = await self._redis.lrange(key, 0, -1)
        if not raw_items:
            await self._redis.srem(_PENDING_ROOMS_KEY, str(itinerary_id))
            return

        parsed_items: list[dict[str, Any]] = []
        for raw in raw_items:
            try:
                as_bytes = raw if isinstance(raw, bytes) else str(raw).encode("utf-8")
                parsed_items.append(json.loads(as_bytes.decode("utf-8")))
            except json.JSONDecodeError:
                continue
        if not parsed_items:
            await self._redis.delete(key)
            await self._redis.srem(_PENDING_ROOMS_KEY, str(itinerary_id))
            return

        with SessionLocal() as db:
            doc_row = db.get(ItineraryCollabDocument, itinerary_id)
            if doc_row is None:
                doc_row = ItineraryCollabDocument(
                    itinerary_id=itinerary_id, state_update=None, update_count=0
                )
                db.add(doc_row)
                db.flush()

            applied = 0
            last_update_bytes: bytes | None = None
            grouped_events: dict[tuple[str, str | None, str | None], dict[str, Any]] = {}
            for payload in parsed_items:
                update_b64 = payload.get("update_b64")
                if not isinstance(update_b64, str) or not update_b64.strip():
                    continue
                try:
                    update_bytes = base64.b64decode(update_b64)
                except ValueError:
                    continue
                last_update_bytes = update_bytes
                actor_type = str(payload.get("participant_type") or "system")
                actor_user_id_raw = payload.get("actor_user_id")
                actor_user_id = None
                if isinstance(actor_user_id_raw, str) and actor_user_id_raw:
                    try:
                        actor_user_id = str(UUID(actor_user_id_raw))
                    except ValueError:
                        actor_user_id = None
                guest_name = payload.get("guest_name")
                guest_value = guest_name if isinstance(guest_name, str) else None
                meta = payload.get("meta")
                origin = ""
                if isinstance(meta, dict):
                    maybe_origin = meta.get("origin")
                    if isinstance(maybe_origin, str):
                        origin = maybe_origin.strip()
                if not origin:
                    origin = "local"
                if origin in {"bootstrap", "seed"}:
                    applied += 1
                    continue
                group_key = (actor_type, actor_user_id, guest_value)
                group = grouped_events.setdefault(
                    group_key,
                    {"bytes": 0, "updates": 0, "origin_counts": {}, "session_ids": set()},
                )
                group["bytes"] += len(update_bytes)
                group["updates"] += 1
                origin_counts = group["origin_counts"]
                origin_counts[origin] = int(origin_counts.get(origin, 0)) + 1
                session_id = payload.get("session_id")
                if isinstance(session_id, str) and session_id:
                    group["session_ids"].add(session_id)
                applied += 1

            for (actor_type, actor_user_id_raw, guest_name), aggregate in grouped_events.items():
                actor_user_id = UUID(actor_user_id_raw) if actor_user_id_raw else None
                session_ids = sorted(list(aggregate["session_ids"]))
                db.add(
                    ItineraryCollabEventLog(
                        itinerary_id=itinerary_id,
                        actor_type=actor_type,
                        actor_user_id=actor_user_id,
                        guest_name=guest_name,
                        event_type="content_sync",
                        target_type="document",
                        target_id=str(itinerary_id),
                        payload={
                            "bytes": int(aggregate["bytes"]),
                            "updates": int(aggregate["updates"]),
                            "origin_counts": aggregate["origin_counts"],
                            "origin": max(
                                aggregate["origin_counts"].items(),
                                key=lambda item: item[1],
                            )[0]
                            if aggregate["origin_counts"]
                            else "local",
                            "session_ids": session_ids,
                        },
                    )
                )

            if applied > 0:
                doc_row.state_update = last_update_bytes
                doc_row.update_count = int(doc_row.update_count or 0) + applied
                db.add(doc_row)
                db.commit()
            else:
                db.rollback()

        await self._redis.delete(key)
        await self._redis.srem(_PENDING_ROOMS_KEY, str(itinerary_id))


_runtime: CollabRuntime | None = None


def get_collab_runtime() -> CollabRuntime:
    global _runtime
    if _runtime is None:
        _runtime = CollabRuntime()
    return _runtime
