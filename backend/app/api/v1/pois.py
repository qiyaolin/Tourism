from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.poi import PoiCreate, PoiListResponse, PoiResponse, PoiUpdate
from app.services.poi_service import create_poi, delete_poi, get_poi, list_pois, update_poi

router = APIRouter(prefix="/pois", tags=["pois"])


@router.post("", response_model=PoiResponse, status_code=status.HTTP_201_CREATED)
def create_poi_api(payload: PoiCreate, db: Session = Depends(get_db)) -> PoiResponse:
    return create_poi(db, payload)


@router.get("", response_model=PoiListResponse)
def list_pois_api(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> PoiListResponse:
    return list_pois(db, offset, limit)


@router.get("/{poi_id}", response_model=PoiResponse)
def get_poi_api(poi_id: UUID, db: Session = Depends(get_db)) -> PoiResponse:
    return get_poi(db, poi_id)


@router.put("/{poi_id}", response_model=PoiResponse)
def update_poi_api(poi_id: UUID, payload: PoiUpdate, db: Session = Depends(get_db)) -> PoiResponse:
    return update_poi(db, poi_id, payload)


@router.delete("/{poi_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_poi_api(poi_id: UUID, db: Session = Depends(get_db)) -> None:
    delete_poi(db, poi_id)

