from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.block import (
    BlockBatchUpdateRequest,
    BlockBatchUpdateResponse,
    BlockCreate,
    BlockDependencyCreate,
    BlockDependencyResponse,
    BlockLayoutUpdate,
    BlockReorderRequest,
    BlockResponse,
    BlockTreeResponse,
    BlockUpdate,
    BoardAutoLayoutResponse,
    BoardResponse,
)
from app.security.deps import get_current_user
from app.services import block_service

router = APIRouter(prefix="/itineraries", tags=["blocks"])


@router.get("/{itinerary_id}/blocks", response_model=BlockTreeResponse)
def get_blocks(
    itinerary_id: UUID,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tree = block_service.list_block_tree(db, itinerary_id)
    return BlockTreeResponse(items=[BlockResponse(**b) for b in tree])


@router.get("/{itinerary_id}/board", response_model=BoardResponse)
def get_board(
    itinerary_id: UUID,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payload = block_service.list_board(db, itinerary_id)
    return BoardResponse(**payload)


@router.post("/{itinerary_id}/blocks", response_model=BlockResponse, status_code=201)
def create_block(
    itinerary_id: UUID,
    data: BlockCreate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = block_service.create_block(db, itinerary_id, data)
        return BlockResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/blocks/{block_id}", response_model=BlockResponse)
def update_block(
    block_id: UUID,
    data: BlockUpdate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = block_service.update_block(db, block_id, data, user.id)
        return BlockResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/blocks/{block_id}/layout", response_model=BlockResponse)
def update_block_layout(
    block_id: UUID,
    data: BlockLayoutUpdate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = block_service.update_block_layout(db, block_id, data)
        return BlockResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/blocks/batch-update", response_model=BlockBatchUpdateResponse)
def batch_update_blocks(
    data: BlockBatchUpdateRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        updated = block_service.batch_update_blocks(db, data)
        return BlockBatchUpdateResponse(updated_count=updated)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/{itinerary_id}/blocks/{block_id}/dependencies",
    response_model=BlockDependencyResponse,
    status_code=201,
)
def create_dependency(
    itinerary_id: UUID,
    block_id: UUID,
    data: BlockDependencyCreate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = block_service.create_dependency(db, itinerary_id, block_id, data)
        return BlockDependencyResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{itinerary_id}/blocks/{block_id}/dependencies/{edge_id}", status_code=204)
def delete_dependency(
    itinerary_id: UUID,
    block_id: UUID,
    edge_id: UUID,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    deleted = block_service.delete_dependency(db, itinerary_id, edge_id, block_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Dependency not found")


@router.delete("/blocks/{block_id}", status_code=204)
def delete_block(
    block_id: UUID,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    deleted = block_service.delete_block(db, block_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Block not found")


@router.post("/{itinerary_id}/blocks/reorder", status_code=204)
def reorder_blocks(
    itinerary_id: UUID,
    data: BlockReorderRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    block_service.reorder_blocks(
        db, itinerary_id, data.parent_block_id, data.day_index, data.ordered_block_ids
    )


@router.post("/{itinerary_id}/board/auto-layout", response_model=BoardAutoLayoutResponse)
def auto_layout_board(
    itinerary_id: UUID,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated_count = block_service.auto_layout_board(db, itinerary_id)
    return BoardAutoLayoutResponse(itinerary_id=itinerary_id, updated_count=updated_count)


@router.post("/{itinerary_id}/blocks/migrate-legacy", response_model=BlockTreeResponse)
def migrate_legacy(
    itinerary_id: UUID,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = block_service.migrate_legacy_items(db, itinerary_id)
    return BlockTreeResponse(items=[BlockResponse(**b) for b in items])


@router.post("/blocks/{block_id}/ungroup", response_model=list[BlockResponse])
def ungroup_block(
    block_id: UUID,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        promoted = block_service.ungroup_block(db, block_id)
        return [BlockResponse(**b) for b in promoted]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
