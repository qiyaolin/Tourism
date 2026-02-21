from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.itinerary import (
    ItineraryCreate,
    ItineraryDiffActionBatchRequest,
    ItineraryDiffActionBatchResponse,
    ItineraryDiffActionStatusResponse,
    ItineraryDiffResponse,
    ItineraryItemCreate,
    ItineraryItemResponse,
    ItineraryItemsWithPoiListResponse,
    ItineraryItemUpdate,
    ItineraryListResponse,
    ItineraryResponse,
    ItineraryUpdate,
)
from app.security.deps import get_current_user
from app.services.itinerary_service import (
    create_item,
    create_itinerary,
    delete_item,
    delete_itinerary,
    get_itinerary,
    get_itinerary_diff,
    get_itinerary_diff_action_statuses,
    list_items_with_poi,
    list_itineraries,
    submit_itinerary_diff_actions_batch,
    update_item,
    update_itinerary,
)

router = APIRouter(prefix="/itineraries", tags=["itineraries"])


@router.post("", response_model=ItineraryResponse, status_code=status.HTTP_201_CREATED)
def create_itinerary_api(
    payload: ItineraryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ItineraryResponse:
    return create_itinerary(db, current_user, payload)


@router.get("", response_model=ItineraryListResponse)
def list_itineraries_api(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ItineraryListResponse:
    return list_itineraries(db, current_user, offset, limit)


@router.get("/{itinerary_id}", response_model=ItineraryResponse)
def get_itinerary_api(
    itinerary_id: UUID,
    collab_grant: str | None = Header(default=None, alias="X-Collab-Grant"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ItineraryResponse:
    return get_itinerary(db, itinerary_id, current_user, collab_grant=collab_grant)


@router.get("/{itinerary_id}/diff", response_model=ItineraryDiffResponse)
def get_itinerary_diff_api(
    itinerary_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ItineraryDiffResponse:
    return get_itinerary_diff(db, itinerary_id, current_user)


@router.post("/{itinerary_id}/diff/actions:batch", response_model=ItineraryDiffActionBatchResponse)
def submit_itinerary_diff_actions_batch_api(
    itinerary_id: UUID,
    payload: ItineraryDiffActionBatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ItineraryDiffActionBatchResponse:
    return submit_itinerary_diff_actions_batch(db, itinerary_id, current_user, payload)


@router.get("/{itinerary_id}/diff/actions", response_model=ItineraryDiffActionStatusResponse)
def get_itinerary_diff_action_statuses_api(
    itinerary_id: UUID,
    source_snapshot_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ItineraryDiffActionStatusResponse:
    return get_itinerary_diff_action_statuses(db, itinerary_id, current_user, source_snapshot_id)


@router.get("/{itinerary_id}/items", response_model=ItineraryItemsWithPoiListResponse)
def list_items_with_poi_api(
    itinerary_id: UUID,
    collab_grant: str | None = Header(default=None, alias="X-Collab-Grant"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ItineraryItemsWithPoiListResponse:
    return list_items_with_poi(db, itinerary_id, current_user, collab_grant=collab_grant)


@router.put("/{itinerary_id}", response_model=ItineraryResponse)
def update_itinerary_api(
    itinerary_id: UUID,
    payload: ItineraryUpdate,
    collab_grant: str | None = Header(default=None, alias="X-Collab-Grant"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ItineraryResponse:
    return update_itinerary(db, itinerary_id, current_user, payload, collab_grant=collab_grant)


@router.delete("/{itinerary_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_itinerary_api(
    itinerary_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    delete_itinerary(db, itinerary_id, current_user)


@router.post(
    "/{itinerary_id}/items",
    response_model=ItineraryItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_item_api(
    itinerary_id: UUID,
    payload: ItineraryItemCreate,
    collab_grant: str | None = Header(default=None, alias="X-Collab-Grant"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ItineraryItemResponse:
    return create_item(db, itinerary_id, current_user, payload, collab_grant=collab_grant)


@router.put("/{itinerary_id}/items/{item_id}", response_model=ItineraryItemResponse)
def update_item_api(
    itinerary_id: UUID,
    item_id: UUID,
    payload: ItineraryItemUpdate,
    collab_grant: str | None = Header(default=None, alias="X-Collab-Grant"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ItineraryItemResponse:
    return update_item(db, itinerary_id, item_id, current_user, payload, collab_grant=collab_grant)


@router.delete("/{itinerary_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item_api(
    itinerary_id: UUID,
    item_id: UUID,
    collab_grant: str | None = Header(default=None, alias="X-Collab-Grant"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    delete_item(db, itinerary_id, item_id, current_user, collab_grant=collab_grant)
