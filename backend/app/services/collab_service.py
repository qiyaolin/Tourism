import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import quote_plus
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.itinerary import Itinerary
from app.models.itinerary_collab import (
    ItineraryCollabEventLog,
    ItineraryCollabLink,
    ItineraryCollabSession,
)
from app.models.user import User
from app.schemas.itinerary_collab import (
    ItineraryCollabHistoryItem,
    ItineraryCollabHistoryListResponse,
    ItineraryCollabLinkCreateRequest,
    ItineraryCollabLinkCreateResponse,
    ItineraryCollabLinkListResponse,
    ItineraryCollabLinkResponse,
    ItineraryCollabLinkUpdateRequest,
)
from app.security.jwt import decode_token


@dataclass
class CollabIdentity:
    permission: Literal["edit", "read"]
    participant_type: Literal["user", "guest"]
    actor_user_id: UUID | None
    guest_name: str | None
    display_name: str
    link_id: UUID | None
    is_owner: bool


def _hash_collab_token(token: str) -> str:
    settings = get_settings()
    digest = hashlib.sha256()
    digest.update(settings.collab_token_secret.encode("utf-8"))
    digest.update(b":")
    digest.update(token.encode("utf-8"))
    return digest.hexdigest()


def _ensure_itinerary_owner(db: Session, itinerary_id: UUID, current_user: User) -> Itinerary:
    itinerary = db.get(Itinerary, itinerary_id)
    if itinerary is None or itinerary.creator_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    return itinerary


def _link_to_response(row: ItineraryCollabLink) -> ItineraryCollabLinkResponse:
    return ItineraryCollabLinkResponse(
        id=row.id,
        itinerary_id=row.itinerary_id,
        permission=row.permission,
        is_revoked=row.is_revoked,
        created_by_user_id=row.created_by_user_id,
        created_at=row.created_at,
        revoked_at=row.revoked_at,
    )


def create_collab_link(
    db: Session,
    itinerary_id: UUID,
    current_user: User,
    payload: ItineraryCollabLinkCreateRequest,
) -> ItineraryCollabLinkCreateResponse:
    _ensure_itinerary_owner(db, itinerary_id, current_user)
    raw_token = secrets.token_urlsafe(24)
    token_hash = _hash_collab_token(raw_token)
    row = ItineraryCollabLink(
        itinerary_id=itinerary_id,
        token_hash=token_hash,
        permission=payload.permission,
        created_by_user_id=current_user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    settings = get_settings()
    base_url = settings.collab_share_base_url.rstrip("/")
    share_url = (
        f"{base_url}?itinerary_id={quote_plus(str(itinerary_id))}"
        f"&collab_token={quote_plus(raw_token)}"
    )
    return ItineraryCollabLinkCreateResponse(
        link=_link_to_response(row), token=raw_token, share_url=share_url
    )


def list_collab_links(
    db: Session,
    itinerary_id: UUID,
    current_user: User,
) -> ItineraryCollabLinkListResponse:
    _ensure_itinerary_owner(db, itinerary_id, current_user)
    rows = db.scalars(
        select(ItineraryCollabLink)
        .where(ItineraryCollabLink.itinerary_id == itinerary_id)
        .order_by(ItineraryCollabLink.created_at.desc())
    ).all()
    return ItineraryCollabLinkListResponse(items=[_link_to_response(row) for row in rows])


def update_collab_link(
    db: Session,
    itinerary_id: UUID,
    link_id: UUID,
    current_user: User,
    payload: ItineraryCollabLinkUpdateRequest,
) -> ItineraryCollabLinkResponse:
    _ensure_itinerary_owner(db, itinerary_id, current_user)
    row = db.get(ItineraryCollabLink, link_id)
    if row is None or row.itinerary_id != itinerary_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collab link not found")
    if payload.permission is not None:
        row.permission = payload.permission
    if payload.revoke is True and not row.is_revoked:
        row.is_revoked = True
        row.revoked_at = datetime.now(UTC)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _link_to_response(row)


def list_collab_history(
    db: Session,
    itinerary_id: UUID,
    current_user: User,
    offset: int,
    limit: int,
) -> ItineraryCollabHistoryListResponse:
    _ensure_itinerary_owner(db, itinerary_id, current_user)
    base = select(ItineraryCollabEventLog).where(
        ItineraryCollabEventLog.itinerary_id == itinerary_id
    )
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(
        base.order_by(ItineraryCollabEventLog.created_at.desc()).offset(offset).limit(limit)
    ).all()
    return ItineraryCollabHistoryListResponse(
        items=[
            ItineraryCollabHistoryItem(
                id=row.id,
                itinerary_id=row.itinerary_id,
                actor_type=row.actor_type,
                actor_user_id=row.actor_user_id,
                guest_name=row.guest_name,
                event_type=row.event_type,
                target_type=row.target_type,
                target_id=row.target_id,
                payload=row.payload,
                created_at=row.created_at,
            )
            for row in rows
        ],
        total=total,
        offset=offset,
        limit=limit,
    )


def validate_collab_link_token(
    db: Session,
    itinerary_id: UUID,
    raw_token: str,
) -> ItineraryCollabLink | None:
    token_hash = _hash_collab_token(raw_token)
    row = db.scalar(
        select(ItineraryCollabLink).where(
            ItineraryCollabLink.itinerary_id == itinerary_id,
            ItineraryCollabLink.token_hash == token_hash,
            ItineraryCollabLink.is_revoked.is_(False),
        )
    )
    return row


def resolve_collab_identity(
    db: Session,
    itinerary_id: UUID,
    *,
    auth_token: str | None,
    collab_token: str | None,
    guest_name: str | None,
) -> CollabIdentity:
    itinerary = db.get(Itinerary, itinerary_id)
    if itinerary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")

    user: User | None = None
    if auth_token:
        try:
            payload = decode_token(auth_token)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            ) from exc
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject"
            )
        try:
            parsed = uuid.UUID(str(user_id))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token format"
            ) from exc
        user = db.get(User, parsed)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if user is not None and user.id == itinerary.creator_user_id:
        return CollabIdentity(
            permission="edit",
            participant_type="user",
            actor_user_id=user.id,
            guest_name=None,
            display_name=user.nickname,
            link_id=None,
            is_owner=True,
        )

    if not collab_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Collab token is required"
        )

    link = validate_collab_link_token(db, itinerary_id, collab_token)
    if link is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid collab token")

    if user is not None:
        return CollabIdentity(
            permission=link.permission,  # type: ignore[arg-type]
            participant_type="user",
            actor_user_id=user.id,
            guest_name=None,
            display_name=user.nickname,
            link_id=link.id,
            is_owner=False,
        )

    display = (guest_name or "").strip()
    if not display:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Guest name is required"
        )
    if len(display) > 64:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Guest name too long")

    return CollabIdentity(
        permission=link.permission,  # type: ignore[arg-type]
        participant_type="guest",
        actor_user_id=None,
        guest_name=display,
        display_name=display,
        link_id=link.id,
        is_owner=False,
    )


def create_collab_session(
    db: Session,
    *,
    itinerary_id: UUID,
    connection_id: str,
    identity: CollabIdentity,
) -> ItineraryCollabSession:
    row = ItineraryCollabSession(
        itinerary_id=itinerary_id,
        link_id=identity.link_id,
        participant_type=identity.participant_type,
        participant_user_id=identity.actor_user_id,
        guest_name=identity.guest_name,
        permission=identity.permission,
        connection_id=connection_id,
    )
    db.add(row)
    db.add(
        ItineraryCollabEventLog(
            itinerary_id=itinerary_id,
            actor_type=identity.participant_type,
            actor_user_id=identity.actor_user_id,
            guest_name=identity.guest_name,
            event_type="join",
            target_type="session",
            target_id=connection_id,
            payload={"permission": identity.permission},
        )
    )
    db.commit()
    db.refresh(row)
    return row


def close_collab_session(
    db: Session,
    *,
    session_id: UUID,
    connection_id: str,
) -> None:
    row = db.get(ItineraryCollabSession, session_id)
    if row is None:
        return
    row.left_at = datetime.now(UTC)
    db.add(row)
    db.add(
        ItineraryCollabEventLog(
            itinerary_id=row.itinerary_id,
            actor_type=row.participant_type,
            actor_user_id=row.participant_user_id,
            guest_name=row.guest_name,
            event_type="leave",
            target_type="session",
            target_id=connection_id,
            payload={},
        )
    )
    db.commit()
