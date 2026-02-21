from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, get_db
from app.models.itinerary_collab import ItineraryCollabSession
from app.models.user import User
from app.schemas.itinerary_collab import (
    ItineraryCollabHistoryListResponse,
    ItineraryCollabLinkCreateRequest,
    ItineraryCollabLinkCreateResponse,
    ItineraryCollabLinkListResponse,
    ItineraryCollabLinkResponse,
    ItineraryCollabLinkUpdateRequest,
)
from app.security.deps import get_current_user
from app.services.collab_runtime import get_collab_runtime
from app.services.collab_service import (
    close_collab_session,
    create_collab_link,
    create_collab_session,
    list_collab_history,
    list_collab_links,
    resolve_collab_identity,
    update_collab_link,
)

router = APIRouter(prefix="/itineraries", tags=["itinerary-collab"])


@router.post(
    "/{itinerary_id}/collab/links",
    response_model=ItineraryCollabLinkCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_collab_link_api(
    itinerary_id: UUID,
    payload: ItineraryCollabLinkCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ItineraryCollabLinkCreateResponse:
    return create_collab_link(db, itinerary_id, current_user, payload)


@router.get("/{itinerary_id}/collab/links", response_model=ItineraryCollabLinkListResponse)
def list_collab_links_api(
    itinerary_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ItineraryCollabLinkListResponse:
    return list_collab_links(db, itinerary_id, current_user)


@router.patch("/{itinerary_id}/collab/links/{link_id}", response_model=ItineraryCollabLinkResponse)
def update_collab_link_api(
    itinerary_id: UUID,
    link_id: UUID,
    payload: ItineraryCollabLinkUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ItineraryCollabLinkResponse:
    return update_collab_link(db, itinerary_id, link_id, current_user, payload)


@router.get("/{itinerary_id}/collab/history", response_model=ItineraryCollabHistoryListResponse)
def list_collab_history_api(
    itinerary_id: UUID,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ItineraryCollabHistoryListResponse:
    return list_collab_history(db, itinerary_id, current_user, offset, limit)


@router.websocket("/{itinerary_id}/collab/ws")
async def itinerary_collab_ws_api(websocket: WebSocket, itinerary_id: UUID) -> None:
    await websocket.accept()
    auth_token = websocket.query_params.get("token")
    collab_token = websocket.query_params.get("collab_token")
    guest_name = websocket.query_params.get("guest_name")

    session_row = None
    conn = None
    runtime = get_collab_runtime()

    with SessionLocal() as db:
        try:
            identity = resolve_collab_identity(
                db,
                itinerary_id,
                auth_token=auth_token,
                collab_token=collab_token,
                guest_name=guest_name,
            )
        except HTTPException as exc:
            await websocket.send_json({"type": "collab:error", "message": str(exc.detail)})
            await websocket.close(code=1008)
            return
        except Exception:
            await websocket.send_json({"type": "collab:error", "message": "collab auth failed"})
            await websocket.close(code=1011)
            return
        session_row = create_collab_session(
            db,
            itinerary_id=itinerary_id,
            connection_id="pending",
            identity=identity,
        )

    try:
        conn = await runtime.register(
            itinerary_id=itinerary_id,
            websocket=websocket,
            identity=identity,
            session_id=session_row.id,
        )
        with SessionLocal() as db:
            session_db = db.get(ItineraryCollabSession, session_row.id)
            if session_db is not None:
                session_db.connection_id = conn.connection_id
                db.add(session_db)
                db.commit()

        while True:
            payload = await websocket.receive_json()
            msg_type = payload.get("type")
            if msg_type == "collab:ping":
                await websocket.send_json({"type": "collab:pong"})
                continue
            if msg_type == "collab:cursor":
                cursor = payload.get("cursor")
                if isinstance(cursor, dict):
                    await runtime.broadcast_cursor(conn, cursor)
                continue
            if msg_type == "collab:update":
                if conn.identity.permission != "edit":
                    await websocket.send_json({"type": "collab:error", "message": "read-only link"})
                    continue
                update_b64 = payload.get("update_b64")
                if not isinstance(update_b64, str) or not update_b64:
                    await websocket.send_json(
                        {"type": "collab:error", "message": "invalid update payload"}
                    )
                    continue
                meta = payload.get("meta")
                await runtime.broadcast_update(
                    conn, update_b64, meta if isinstance(meta, dict) else {}
                )
                continue
            await websocket.send_json(
                {"type": "collab:error", "message": "unsupported message type"}
            )
    except WebSocketDisconnect:
        pass
    finally:
        if conn is not None:
            await runtime.unregister(conn)
        if session_row is not None:
            with SessionLocal() as db:
                close_collab_session(
                    db,
                    session_id=session_row.id,
                    connection_id=conn.connection_id if conn is not None else "pending",
                )
