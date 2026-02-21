from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.schemas.itinerary_collab import CollabCodeResolveRequest
from app.services.collab_service import (
    CollabGrantClaims,
    resolve_collab_code_for_user,
    resolve_itinerary_access,
)


class _FakeDb:
    def __init__(self, *, itinerary=None, link=None):
        self._itinerary = itinerary
        self._link = link

    def get(self, model, entity_id):
        model_name = getattr(model, "__name__", "")
        if model_name == "Itinerary" and self._itinerary and entity_id == self._itinerary.id:
            return self._itinerary
        if model_name == "ItineraryCollabLink" and self._link and entity_id == self._link.id:
            return self._link
        return None


def test_resolve_collab_code_for_user_returns_grant(monkeypatch):
    itinerary_id = uuid4()
    link_id = uuid4()
    db = _FakeDb(
        itinerary=SimpleNamespace(id=itinerary_id, title="共享测试行程"),
        link=SimpleNamespace(id=link_id, itinerary_id=itinerary_id, permission="edit", is_revoked=False),
    )
    current_user = SimpleNamespace(id=uuid4())

    monkeypatch.setattr(
        "app.services.collab_service._resolve_link_for_code",
        lambda _db, _code: db._link,
    )
    monkeypatch.setattr(
        "app.services.collab_service._create_collab_grant",
        lambda **_kwargs: ("grant-token", 7200),
    )

    result = resolve_collab_code_for_user(
        db,
        current_user=current_user,
        payload=CollabCodeResolveRequest(code="A9K3M2QX"),
    )

    assert result.itinerary_id == itinerary_id
    assert result.permission == "edit"
    assert result.collab_grant == "grant-token"
    assert result.expires_in == 7200


def test_resolve_itinerary_access_allows_collaborator_edit(monkeypatch):
    itinerary_id = uuid4()
    owner_id = uuid4()
    user_id = uuid4()
    link_id = uuid4()
    itinerary = SimpleNamespace(id=itinerary_id, creator_user_id=owner_id)
    link = SimpleNamespace(
        id=link_id,
        itinerary_id=itinerary_id,
        permission="edit",
        is_revoked=False,
    )
    db = _FakeDb(itinerary=itinerary, link=link)
    current_user = SimpleNamespace(id=user_id)

    monkeypatch.setattr(
        "app.services.collab_service._decode_collab_grant",
        lambda _grant, **_kwargs: CollabGrantClaims(
            user_id=user_id,
            itinerary_id=itinerary_id,
            permission="edit",
            link_id=link_id,
        ),
    )

    context = resolve_itinerary_access(
        db,
        itinerary_id,
        current_user,
        collab_grant="grant-token",
        require_edit=True,
    )

    assert context.is_owner is False
    assert context.permission == "edit"
    assert context.link_id == link_id


def test_resolve_itinerary_access_rejects_missing_grant():
    itinerary_id = uuid4()
    owner_id = uuid4()
    current_user = SimpleNamespace(id=uuid4())
    db = _FakeDb(itinerary=SimpleNamespace(id=itinerary_id, creator_user_id=owner_id))

    with pytest.raises(HTTPException) as exc:
        resolve_itinerary_access(
            db,
            itinerary_id,
            current_user,
            collab_grant=None,
            require_edit=False,
        )

    assert exc.value.status_code == 404
