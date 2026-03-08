from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.block import (
    TemplateForkRequest,
    TemplateListResponse,
    TemplatePublish,
    TemplateRatingCreate,
    TemplateResponse,
)
from app.security.deps import get_current_user
from app.services import block_template_service

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=TemplateListResponse)
def list_templates(
    block_type: str | None = Query(default=None),
    style_tag: str | None = Query(default=None),
    region_name: str | None = Query(default=None),
    search: str | None = Query(default=None),
    sort_by: str = Query(default="hot"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items, total = block_template_service.list_templates(
        db,
        block_type=block_type,
        style_tag=style_tag,
        region_name=region_name,
        search=search,
        sort_by=sort_by,
        offset=offset,
        limit=limit,
    )
    return TemplateListResponse(
        items=[TemplateResponse(**t) for t in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: UUID,
    db: Session = Depends(get_db),
):
    result = block_template_service.get_template(db, template_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return TemplateResponse(**result)


@router.post("", response_model=TemplateResponse, status_code=201)
def publish_template(
    data: TemplatePublish,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = block_template_service.publish_template(
        db,
        user_id=user.id,
        title=data.title,
        description=data.description,
        style_tags=data.style_tags,
        block_type=data.block_type,
        is_group=data.is_group,
        content_snapshot=data.content_snapshot,
        children_snapshot=data.children_snapshot,
        longitude=data.longitude,
        latitude=data.latitude,
        region_name=data.region_name,
    )
    return TemplateResponse(**result)


@router.post("/{template_id}/fork", status_code=201)
def fork_template(
    template_id: UUID,
    data: TemplateForkRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        blocks = block_template_service.fork_template_to_blocks(
            db,
            template_id=template_id,
            itinerary_id=data.itinerary_id,
            day_index=data.day_index,
            sort_order=data.sort_order,
            lane_key=data.lane_key,
            parent_block_id=data.parent_block_id,
        )
        return {"created_blocks": blocks}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{template_id}/rate", response_model=TemplateResponse, status_code=201)
def rate_template(
    template_id: UUID,
    data: TemplateRatingCreate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = block_template_service.rate_template(
            db,
            template_id=template_id,
            user_id=user.id,
            score=data.score,
            comment=data.comment,
        )
        return TemplateResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
