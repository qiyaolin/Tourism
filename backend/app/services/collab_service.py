import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from urllib.parse import quote_plus
from uuid import UUID

from fastapi import HTTPException, status
from jose import JWTError, jwt
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
    CollabCodeResolveRequest,
    CollabCodeResolveResponse,
    ItineraryCollabHistoryItem,
    ItineraryCollabHistoryListResponse,
    ItineraryCollabLinkCreateRequest,
    ItineraryCollabLinkCreateResponse,
    ItineraryCollabLinkListResponse,
    ItineraryCollabLinkResponse,
    ItineraryCollabLinkUpdateRequest,
)
from app.security.jwt import decode_token

COLLAB_SHARE_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
COLLAB_SHARE_CODE_LENGTH = 8
COLLAB_GRANT_SCOPE = "collab_grant"


@dataclass
class CollabIdentity:
    permission: Literal["edit", "read"]
    participant_type: Literal["user", "guest"]
    actor_user_id: UUID | None
    guest_name: str | None
    display_name: str
    link_id: UUID | None
    is_owner: bool


@dataclass
class CollabGrantClaims:
    user_id: UUID
    itinerary_id: UUID
    permission: Literal["edit", "read"]
    link_id: UUID


@dataclass
class ItineraryAccessContext:
    itinerary: Itinerary
    permission: Literal["edit", "read"]
    is_owner: bool
    link_id: UUID | None


def _hash_with_secret(value: str, *, scope: str) -> str:
    settings = get_settings()
    digest = hashlib.sha256()
    digest.update(settings.collab_token_secret.encode("utf-8"))
    digest.update(b":")
    digest.update(scope.encode("utf-8"))
    digest.update(b":")
    digest.update(value.encode("utf-8"))
    return digest.hexdigest()


def _hash_collab_token(token: str) -> str:
    return _hash_with_secret(token, scope="token")


def _hash_share_code(code: str) -> str:
    return _hash_with_secret(code.upper(), scope="share_code")


def _collab_signing_secret() -> str:
    settings = get_settings()
    if settings.collab_grant_secret.strip():
        return settings.collab_grant_secret
    return settings.jwt_secret


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
        share_code_last4=row.share_code_last4,
        is_revoked=row.is_revoked,
        created_by_user_id=row.created_by_user_id,
        created_at=row.created_at,
        revoked_at=row.revoked_at,
    )


def _generate_share_code() -> str:
    return "".join(
        secrets.choice(COLLAB_SHARE_CODE_ALPHABET) for _ in range(COLLAB_SHARE_CODE_LENGTH)
    )


def _build_share_url(share_code: str) -> str:
    settings = get_settings()
    base_url = settings.collab_share_base_url.rstrip("/")
    return f"{base_url}?code={quote_plus(share_code)}"


def _create_collab_grant(
    *,
    user_id: UUID,
    itinerary_id: UUID,
    link_id: UUID,
    permission: Literal["edit", "read"],
) -> tuple[str, int]:
    settings = get_settings()
    now = datetime.now(UTC)
    expires_in = max(60, settings.collab_grant_expires_minutes * 60)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "scope": COLLAB_GRANT_SCOPE,
        "itinerary_id": str(itinerary_id),
        "permission": permission,
        "link_id": str(link_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
    }
    token = jwt.encode(payload, _collab_signing_secret(), algorithm=settings.jwt_algorithm)
    return token, expires_in


def _decode_collab_grant(
    grant: str,
    *,
    expected_user_id: UUID,
    expected_itinerary_id: UUID,
) -> CollabGrantClaims:
    settings = get_settings()
    try:
        payload = jwt.decode(
            grant,
            _collab_signing_secret(),
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid collab grant") from exc

    if payload.get("scope") != COLLAB_GRANT_SCOPE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid collab grant scope")
    try:
        user_id = UUID(str(payload.get("sub")))
        itinerary_id = UUID(str(payload.get("itinerary_id")))
        link_id = UUID(str(payload.get("link_id")))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid collab grant payload") from exc

    if user_id != expected_user_id or itinerary_id != expected_itinerary_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Collab grant does not match current user or itinerary")

    permission_value = str(payload.get("permission") or "read")
    if permission_value not in {"edit", "read"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid collab permission")

    return CollabGrantClaims(
        user_id=user_id,
        itinerary_id=itinerary_id,
        permission=permission_value,  # type: ignore[arg-type]
        link_id=link_id,
    )


def _resolve_link_for_code(db: Session, share_code: str) -> ItineraryCollabLink | None:
    if not share_code:
        return None
    return db.scalar(
        select(ItineraryCollabLink).where(
            ItineraryCollabLink.share_code_hash == _hash_share_code(share_code),
            ItineraryCollabLink.is_revoked.is_(False),
        )
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

    share_code = ""
    share_code_hash = ""
    for _ in range(10):
        candidate = _generate_share_code()
        candidate_hash = _hash_share_code(candidate)
        existed = db.scalar(
            select(ItineraryCollabLink.id).where(ItineraryCollabLink.share_code_hash == candidate_hash)
        )
        if existed is None:
            share_code = candidate
            share_code_hash = candidate_hash
            break
    if not share_code:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to allocate share code")

    row = ItineraryCollabLink(
        itinerary_id=itinerary_id,
        token_hash=token_hash,
        share_code_hash=share_code_hash,
        share_code_last4=share_code[-4:],
        permission=payload.permission,
        created_by_user_id=current_user.id,
    )
    db.add(row)
    db.add(
        ItineraryCollabEventLog(
            itinerary_id=itinerary_id,
            actor_type="user",
            actor_user_id=current_user.id,
            guest_name=None,
            event_type="share_code_created",
            target_type="collab_link",
            target_id=str(row.id),
            payload={
                "permission": row.permission,
                "share_code_last4": row.share_code_last4,
            },
        )
    )
    db.commit()
    db.refresh(row)

    return ItineraryCollabLinkCreateResponse(
        link=_link_to_response(row),
        share_code=share_code,
        share_url=_build_share_url(share_code),
    )


def resolve_collab_code_for_user(
    db: Session,
    *,
    current_user: User,
    payload: CollabCodeResolveRequest,
) -> CollabCodeResolveResponse:
    code = payload.code.strip().upper()
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Share code is required")
    link = _resolve_link_for_code(db, code)
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share code not found")
    itinerary = db.get(Itinerary, link.itinerary_id)
    if itinerary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    grant, expires_in = _create_collab_grant(
        user_id=current_user.id,
        itinerary_id=itinerary.id,
        link_id=link.id,
        permission=link.permission,  # type: ignore[arg-type]
    )
    return CollabCodeResolveResponse(
        itinerary_id=itinerary.id,
        itinerary_title=itinerary.title,
        permission=link.permission,  # type: ignore[arg-type]
        collab_grant=grant,
        expires_in=expires_in,
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
    old_permission = row.permission
    if payload.permission is not None:
        row.permission = payload.permission
    if old_permission != row.permission:
        db.add(
            ItineraryCollabEventLog(
                itinerary_id=itinerary_id,
                actor_type="user",
                actor_user_id=current_user.id,
                guest_name=None,
                event_type="link_permission_changed",
                target_type="collab_link",
                target_id=str(row.id),
                payload={"from": old_permission, "to": row.permission},
            )
        )
    if payload.revoke is True and not row.is_revoked:
        row.is_revoked = True
        row.revoked_at = datetime.now(UTC)
        db.add(
            ItineraryCollabEventLog(
                itinerary_id=itinerary_id,
                actor_type="user",
                actor_user_id=current_user.id,
                guest_name=None,
                event_type="share_code_revoked",
                target_type="collab_link",
                target_id=str(row.id),
                payload={"share_code_last4": row.share_code_last4},
            )
        )
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
        ItineraryCollabEventLog.itinerary_id == itinerary_id,
        ItineraryCollabEventLog.event_type.notin_(("join", "leave")),
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
    return db.scalar(
        select(ItineraryCollabLink).where(
            ItineraryCollabLink.itinerary_id == itinerary_id,
            ItineraryCollabLink.token_hash == token_hash,
            ItineraryCollabLink.is_revoked.is_(False),
        )
    )


def resolve_itinerary_access(
    db: Session,
    itinerary_id: UUID,
    current_user: User,
    *,
    collab_grant: str | None,
    require_edit: bool,
) -> ItineraryAccessContext:
    itinerary = db.get(Itinerary, itinerary_id)
    if itinerary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    if itinerary.creator_user_id == current_user.id:
        return ItineraryAccessContext(
            itinerary=itinerary,
            permission="edit",
            is_owner=True,
            link_id=None,
        )
    if not collab_grant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")

    claims = _decode_collab_grant(
        collab_grant,
        expected_user_id=current_user.id,
        expected_itinerary_id=itinerary_id,
    )
    link = db.get(ItineraryCollabLink, claims.link_id)
    if link is None or link.itinerary_id != itinerary_id or link.is_revoked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Collab grant is no longer valid")
    permission = link.permission  # type: ignore[assignment]
    if require_edit and permission != "edit":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="read-only collab permission")
    return ItineraryAccessContext(
        itinerary=itinerary,
        permission=permission,
        is_owner=False,
        link_id=link.id,
    )


def resolve_collab_identity(
    db: Session,
    itinerary_id: UUID,
    *,
    auth_token: str | None,
    collab_grant: str | None,
    collab_token: str | None,
) -> CollabIdentity:
    itinerary = db.get(Itinerary, itinerary_id)
    if itinerary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Itinerary not found")
    if not auth_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required")

    try:
        payload = decode_token(auth_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
    try:
        parsed = uuid.UUID(str(user_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token format") from exc
    user = db.get(User, parsed)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if user.id == itinerary.creator_user_id:
        return CollabIdentity(
            permission="edit",
            participant_type="user",
            actor_user_id=user.id,
            guest_name=None,
            display_name=user.nickname,
            link_id=None,
            is_owner=True,
        )

    if collab_grant:
        claims = _decode_collab_grant(
            collab_grant,
            expected_user_id=user.id,
            expected_itinerary_id=itinerary_id,
        )
        link = db.get(ItineraryCollabLink, claims.link_id)
        if link is None or link.itinerary_id != itinerary_id or link.is_revoked:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Collab grant is no longer valid")
        return CollabIdentity(
            permission=link.permission,  # type: ignore[arg-type]
            participant_type="user",
            actor_user_id=user.id,
            guest_name=None,
            display_name=user.nickname,
            link_id=link.id,
            is_owner=False,
        )

    # Legacy compatibility for existing shared URLs during transition.
    if collab_token:
        link = validate_collab_link_token(db, itinerary_id, collab_token)
        if link is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid collab token")
        return CollabIdentity(
            permission=link.permission,  # type: ignore[arg-type]
            participant_type="user",
            actor_user_id=user.id,
            guest_name=None,
            display_name=user.nickname,
            link_id=link.id,
            is_owner=False,
        )

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Collab grant is required")


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
