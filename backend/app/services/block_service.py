import uuid
from collections import defaultdict
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.itinerary_block import ItineraryBlock
from app.models.itinerary_block_edge import ItineraryBlockEdge
from app.models.itinerary_item import ItineraryItem
from app.models.poi import Poi
from app.schemas.block import (
    VALID_BLOCK_STATUSES,
    VALID_BLOCK_TYPES,
    VALID_EDGE_TYPES,
    VALID_PRIORITY_LEVELS,
    VALID_RISK_LEVELS,
    BlockBatchUpdateRequest,
    BlockCreate,
    BlockDependencyCreate,
    BlockLayoutUpdate,
    BlockUpdate,
)

DEFAULT_LANE_LABELS = {
    "core": "核心流程",
    "transit": "交通",
    "scenic": "景点",
    "dining": "餐饮",
    "lodging": "住宿",
    "activity": "活动",
    "note": "备注",
}


def list_block_tree(db: Session, itinerary_id: uuid.UUID) -> list[dict[str, Any]]:
    """Return all blocks for an itinerary as a nested tree."""
    rows = _query_blocks(db, itinerary_id)
    return _build_block_tree(rows)


def list_board(db: Session, itinerary_id: uuid.UUID) -> dict[str, Any]:
    rows = _query_blocks(db, itinerary_id)
    tree = _build_block_tree(rows)
    dependencies = list_dependencies(db, itinerary_id)
    lane_stats: dict[str, dict[str, int | str]] = {}
    for row in rows:
        lane_key = row.lane_key or "core"
        if lane_key not in lane_stats:
            lane_stats[lane_key] = {
                "lane_key": lane_key,
                "label": DEFAULT_LANE_LABELS.get(lane_key, lane_key),
                "block_count": 0,
                "done_count": 0,
            }
        lane_stats[lane_key]["block_count"] = int(lane_stats[lane_key]["block_count"]) + 1
        if row.status == "done":
            lane_stats[lane_key]["done_count"] = int(lane_stats[lane_key]["done_count"]) + 1
    return {
        "itinerary_id": itinerary_id,
        "items": tree,
        "dependencies": dependencies,
        "lanes": sorted(lane_stats.values(), key=lambda item: str(item["lane_key"])),
        "summary": {
            "block_count": len(rows),
            "dependency_count": len(dependencies),
            "blocked_count": sum(1 for row in rows if row.status == "blocked"),
        },
    }


def create_block(
    db: Session,
    itinerary_id: uuid.UUID,
    data: BlockCreate,
) -> dict[str, Any]:
    """Create a new block in an itinerary."""
    _validate_block_type(data.block_type)
    _validate_status(data.status)
    _validate_priority(data.priority)
    _validate_risk_level(data.risk_level)
    _validate_lane_key(data.lane_key)
    _validate_minute_range(data.start_minute, data.end_minute)

    block = ItineraryBlock(
        itinerary_id=itinerary_id,
        parent_block_id=data.parent_block_id,
        sort_order=data.sort_order,
        day_index=data.day_index,
        lane_key=data.lane_key,
        start_minute=data.start_minute,
        end_minute=data.end_minute,
        block_type=data.block_type,
        title=data.title,
        duration_minutes=data.duration_minutes,
        cost=float(data.cost) if data.cost is not None else None,
        tips=data.tips,
        address=data.address,
        photos=data.photos,
        type_data=data.type_data,
        is_container=data.is_container,
        source_template_id=data.source_template_id,
        status=data.status,
        priority=data.priority,
        risk_level=data.risk_level,
        assignee_user_id=data.assignee_user_id,
        tags=data.tags,
        ui_meta=data.ui_meta,
    )
    db.add(block)
    db.flush()
    _update_geom(db, block.id, data.longitude, data.latitude)
    db.commit()
    db.refresh(block)
    return _row_to_dict(block)


def update_block(
    db: Session,
    block_id: uuid.UUID,
    data: BlockUpdate,
    user_id: uuid.UUID,
) -> dict[str, Any]:
    """Update an existing block."""
    stmt = select(ItineraryBlock).where(ItineraryBlock.id == block_id)
    result = db.execute(stmt)
    block = result.scalar_one_or_none()
    if block is None:
        raise ValueError("Block not found")

    patch = data.model_dump(exclude_unset=True)
    lng = patch.pop("longitude", None)
    lat = patch.pop("latitude", None)
    _validate_patch(patch)

    for key, value in patch.items():
        if key == "cost" and value is not None:
            value = float(value)
        setattr(block, key, value)

    _validate_minute_range(block.start_minute, block.end_minute)
    _update_geom(db, block_id, lng, lat)
    db.commit()
    db.refresh(block)
    return _row_to_dict(block)


def update_block_layout(
    db: Session,
    block_id: uuid.UUID,
    payload: BlockLayoutUpdate,
) -> dict[str, Any]:
    stmt = select(ItineraryBlock).where(ItineraryBlock.id == block_id)
    result = db.execute(stmt)
    block = result.scalar_one_or_none()
    if block is None:
        raise ValueError("Block not found")

    patch = payload.model_dump(exclude_unset=True)
    if "lane_key" in patch:
        _validate_lane_key(str(patch["lane_key"]))
    next_start = patch.get("start_minute", block.start_minute)
    next_end = patch.get("end_minute", block.end_minute)
    _validate_minute_range(next_start, next_end)

    for key, value in patch.items():
        setattr(block, key, value)
    db.commit()
    db.refresh(block)
    return _row_to_dict(block)


def batch_update_blocks(
    db: Session,
    payload: BlockBatchUpdateRequest,
) -> int:
    if payload.status is not None:
        _validate_status(payload.status)
    if payload.priority is not None:
        _validate_priority(payload.priority)
    if payload.risk_level is not None:
        _validate_risk_level(payload.risk_level)
    updates: dict[str, Any] = {}
    for field in ("status", "priority", "risk_level", "assignee_user_id", "tags"):
        value = getattr(payload, field)
        if value is not None:
            updates[field] = value
    if not updates:
        return 0

    stmt = select(ItineraryBlock).where(
        ItineraryBlock.itinerary_id == payload.itinerary_id,
        ItineraryBlock.id.in_(payload.block_ids),
    )
    rows = db.execute(stmt).scalars().all()
    for row in rows:
        for key, value in updates.items():
            setattr(row, key, value)
    db.commit()
    return len(rows)


def delete_block(db: Session, block_id: uuid.UUID) -> bool:
    """Delete a block and all its children (CASCADE)."""
    stmt = select(ItineraryBlock).where(ItineraryBlock.id == block_id)
    result = db.execute(stmt)
    block = result.scalar_one_or_none()
    if block is None:
        return False
    db.delete(block)
    db.commit()
    return True


def reorder_blocks(
    db: Session,
    itinerary_id: uuid.UUID,
    parent_block_id: uuid.UUID | None,
    day_index: int,
    ordered_ids: list[uuid.UUID],
) -> None:
    """Reorder blocks within a container/day."""
    for idx, block_id in enumerate(ordered_ids, start=1):
        db.execute(
            text(
                "UPDATE itinerary_blocks "
                "SET sort_order = :order, day_index = :day "
                "WHERE id = :id AND itinerary_id = :itin_id"
            ),
            {"order": idx, "day": day_index, "id": str(block_id), "itin_id": str(itinerary_id)},
        )
    db.commit()


def auto_layout_board(db: Session, itinerary_id: uuid.UUID) -> int:
    rows = _query_blocks(db, itinerary_id)
    grouped: dict[tuple[int, str], list[ItineraryBlock]] = defaultdict(list)
    for row in rows:
        if row.parent_block_id is not None:
            continue
        grouped[(row.day_index, row.lane_key or "core")].append(row)

    updated = 0
    for items in grouped.values():
        items.sort(
            key=lambda row: (
                row.start_minute if row.start_minute is not None else 10**9,
                row.sort_order,
                str(row.id),
            )
        )
        for idx, row in enumerate(items, start=1):
            if row.sort_order != idx:
                row.sort_order = idx
                updated += 1
    db.commit()
    return updated


def create_dependency(
    db: Session,
    itinerary_id: uuid.UUID,
    from_block_id: uuid.UUID,
    payload: BlockDependencyCreate,
) -> dict[str, Any]:
    _validate_edge_type(payload.edge_type)
    if from_block_id == payload.to_block_id:
        raise ValueError("A block cannot depend on itself")

    source = _get_block(db, from_block_id)
    target = _get_block(db, payload.to_block_id)
    if source is None or target is None:
        raise ValueError("Block not found")
    if source.itinerary_id != itinerary_id or target.itinerary_id != itinerary_id:
        raise ValueError("Dependency blocks must belong to the itinerary")

    existing_edges = db.execute(
        select(ItineraryBlockEdge).where(ItineraryBlockEdge.itinerary_id == itinerary_id)
    ).scalars().all()
    if _would_create_cycle(existing_edges, from_block_id, payload.to_block_id):
        raise ValueError("Dependency cycle detected")

    for edge in existing_edges:
        if edge.from_block_id == from_block_id and edge.to_block_id == payload.to_block_id:
            raise ValueError("Dependency already exists")

    edge = ItineraryBlockEdge(
        itinerary_id=itinerary_id,
        from_block_id=from_block_id,
        to_block_id=payload.to_block_id,
        edge_type=payload.edge_type,
    )
    db.add(edge)
    db.commit()
    db.refresh(edge)
    return _edge_to_dict(edge)


def delete_dependency(
    db: Session,
    itinerary_id: uuid.UUID,
    edge_id: uuid.UUID,
    from_block_id: uuid.UUID,
) -> bool:
    edge = db.execute(
        select(ItineraryBlockEdge).where(
            ItineraryBlockEdge.id == edge_id,
            ItineraryBlockEdge.itinerary_id == itinerary_id,
            ItineraryBlockEdge.from_block_id == from_block_id,
        )
    ).scalar_one_or_none()
    if edge is None:
        return False
    db.delete(edge)
    db.commit()
    return True


def list_dependencies(db: Session, itinerary_id: uuid.UUID) -> list[dict[str, Any]]:
    rows = db.execute(
        select(ItineraryBlockEdge)
        .where(ItineraryBlockEdge.itinerary_id == itinerary_id)
        .order_by(ItineraryBlockEdge.created_at.asc())
    ).scalars().all()
    return [_edge_to_dict(item) for item in rows]


def migrate_legacy_items(db: Session, itinerary_id: uuid.UUID) -> list[dict[str, Any]]:
    """Migrate legacy itinerary_items to itinerary_blocks (one-time)."""
    existing = db.execute(
        select(func.count())
        .select_from(ItineraryBlock)
        .where(ItineraryBlock.itinerary_id == itinerary_id)
    )
    if existing.scalar() > 0:
        return []

    stmt = (
        select(ItineraryItem, Poi)
        .join(Poi, ItineraryItem.poi_id == Poi.id)
        .where(ItineraryItem.itinerary_id == itinerary_id)
        .order_by(ItineraryItem.day_index, ItineraryItem.sort_order)
    )
    rows = db.execute(stmt).all()

    created: list[dict[str, Any]] = []
    for item, poi in rows:
        block = ItineraryBlock(
            itinerary_id=itinerary_id,
            parent_block_id=None,
            sort_order=item.sort_order,
            day_index=item.day_index,
            lane_key="scenic",
            start_minute=None,
            end_minute=None,
            block_type="scenic",
            title=poi.name,
            duration_minutes=item.duration_minutes,
            cost=float(item.cost) if item.cost is not None else None,
            tips=item.tips,
            address=poi.address,
            photos=None,
            type_data={
                "opening_hours": poi.opening_hours,
                "ticket_price": float(poi.ticket_price) if poi.ticket_price is not None else None,
                "poi_id": str(poi.id),
            },
            is_container=False,
            source_template_id=None,
            status="draft",
            priority="medium",
            risk_level="low",
            assignee_user_id=None,
            tags=None,
            ui_meta=None,
        )
        db.add(block)
        db.flush()
        if poi.geom is not None:
            db.execute(
                text(
                    "UPDATE itinerary_blocks SET location_geom = p.geom "
                    "FROM pois p WHERE p.id = :poi_id AND itinerary_blocks.id = :block_id"
                ),
                {"poi_id": str(poi.id), "block_id": str(block.id)},
            )
        created.append(_row_to_dict(block))

    db.commit()
    return created


def ungroup_block(db: Session, block_id: uuid.UUID) -> list[dict[str, Any]]:
    """Ungroup a container: promote all children to the container's parent level."""
    stmt = select(ItineraryBlock).where(ItineraryBlock.id == block_id)
    result = db.execute(stmt)
    container = result.scalar_one_or_none()
    if container is None:
        raise ValueError("Block not found")
    if not container.is_container:
        raise ValueError("Block is not a container, cannot ungroup")

    children_stmt = (
        select(ItineraryBlock)
        .where(ItineraryBlock.parent_block_id == block_id)
        .order_by(ItineraryBlock.sort_order)
    )
    children = db.execute(children_stmt).scalars().all()

    promoted: list[dict[str, Any]] = []
    base_order = container.sort_order
    for idx, child in enumerate(children):
        child.parent_block_id = container.parent_block_id
        child.day_index = container.day_index
        child.sort_order = base_order + idx
        promoted.append(_row_to_dict(child))

    db.delete(container)
    db.commit()
    return promoted


def _query_blocks(db: Session, itinerary_id: uuid.UUID) -> list[ItineraryBlock]:
    stmt = (
        select(ItineraryBlock)
        .where(ItineraryBlock.itinerary_id == itinerary_id)
        .order_by(
            ItineraryBlock.day_index,
            ItineraryBlock.lane_key,
            ItineraryBlock.sort_order,
            ItineraryBlock.created_at,
        )
    )
    return db.execute(stmt).scalars().all()


def _build_block_tree(rows: list[ItineraryBlock]) -> list[dict[str, Any]]:
    block_map: dict[uuid.UUID, dict[str, Any]] = {}
    for row in rows:
        block_map[row.id] = _row_to_dict(row)

    roots: list[dict[str, Any]] = []
    for block in block_map.values():
        pid = block["parent_block_id"]
        if pid and pid in block_map:
            block_map[pid]["children"].append(block)
        else:
            roots.append(block)

    for block in block_map.values():
        block["children"].sort(
            key=lambda b: (
                b["day_index"],
                str(b.get("lane_key") or "core"),
                b["sort_order"],
                str(b["id"]),
            )
        )
    roots.sort(
        key=lambda b: (
            b["day_index"],
            str(b.get("lane_key") or "core"),
            b["sort_order"],
            str(b["id"]),
        )
    )
    return roots


def _validate_patch(patch: dict[str, Any]) -> None:
    if "block_type" in patch and patch["block_type"] is not None:
        _validate_block_type(str(patch["block_type"]))
    if "status" in patch and patch["status"] is not None:
        _validate_status(str(patch["status"]))
    if "priority" in patch and patch["priority"] is not None:
        _validate_priority(str(patch["priority"]))
    if "risk_level" in patch and patch["risk_level"] is not None:
        _validate_risk_level(str(patch["risk_level"]))
    if "lane_key" in patch and patch["lane_key"] is not None:
        _validate_lane_key(str(patch["lane_key"]))


def _validate_block_type(value: str) -> None:
    if value not in VALID_BLOCK_TYPES:
        raise ValueError(f"Invalid block_type: {value}")


def _validate_status(value: str) -> None:
    if value not in VALID_BLOCK_STATUSES:
        raise ValueError(f"Invalid status: {value}")


def _validate_priority(value: str) -> None:
    if value not in VALID_PRIORITY_LEVELS:
        raise ValueError(f"Invalid priority: {value}")


def _validate_risk_level(value: str) -> None:
    if value not in VALID_RISK_LEVELS:
        raise ValueError(f"Invalid risk_level: {value}")


def _validate_edge_type(value: str) -> None:
    if value not in VALID_EDGE_TYPES:
        raise ValueError(f"Invalid edge_type: {value}")


def _validate_lane_key(value: str) -> None:
    normalized = value.strip()
    if not normalized:
        raise ValueError("lane_key cannot be empty")
    if len(normalized) > 32:
        raise ValueError("lane_key too long")


def _validate_minute_range(start_minute: int | None, end_minute: int | None) -> None:
    if start_minute is not None and end_minute is not None and end_minute < start_minute:
        raise ValueError("end_minute must be greater than or equal to start_minute")


def _get_block(db: Session, block_id: uuid.UUID) -> ItineraryBlock | None:
    stmt = select(ItineraryBlock).where(ItineraryBlock.id == block_id)
    return db.execute(stmt).scalar_one_or_none()


def _would_create_cycle(
    edges: list[ItineraryBlockEdge],
    from_block_id: uuid.UUID,
    to_block_id: uuid.UUID,
) -> bool:
    graph: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    for edge in edges:
        graph[edge.from_block_id].append(edge.to_block_id)
    graph[from_block_id].append(to_block_id)

    stack = [to_block_id]
    visited: set[uuid.UUID] = set()
    while stack:
        node = stack.pop()
        if node == from_block_id:
            return True
        if node in visited:
            continue
        visited.add(node)
        for nxt in graph.get(node, []):
            if nxt not in visited:
                stack.append(nxt)
    return False


def _update_geom(db: Session, block_id: uuid.UUID, lng: float | None, lat: float | None) -> None:
    if lng is None or lat is None:
        return
    db.execute(
        text(
            "UPDATE itinerary_blocks "
            "SET location_geom = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326) "
            "WHERE id = :id"
        ),
        {"lng": lng, "lat": lat, "id": str(block_id)},
    )


def _edge_to_dict(edge: ItineraryBlockEdge) -> dict[str, Any]:
    return {
        "id": edge.id,
        "itinerary_id": edge.itinerary_id,
        "from_block_id": edge.from_block_id,
        "to_block_id": edge.to_block_id,
        "edge_type": edge.edge_type,
        "created_at": edge.created_at,
    }


def _row_to_dict(block: ItineraryBlock) -> dict[str, Any]:
    """Convert a block ORM row to a response dict."""
    lng = None
    lat = None
    return {
        "id": block.id,
        "itinerary_id": block.itinerary_id,
        "parent_block_id": block.parent_block_id,
        "sort_order": block.sort_order,
        "day_index": block.day_index,
        "lane_key": block.lane_key,
        "start_minute": block.start_minute,
        "end_minute": block.end_minute,
        "block_type": block.block_type,
        "title": block.title,
        "duration_minutes": block.duration_minutes,
        "cost": float(block.cost) if block.cost is not None else None,
        "tips": block.tips,
        "longitude": lng,
        "latitude": lat,
        "address": block.address,
        "photos": block.photos,
        "type_data": block.type_data,
        "is_container": block.is_container,
        "source_template_id": block.source_template_id,
        "status": block.status,
        "priority": block.priority,
        "risk_level": block.risk_level,
        "assignee_user_id": block.assignee_user_id,
        "tags": block.tags,
        "ui_meta": block.ui_meta,
        "children": [],
        "created_at": block.created_at,
        "updated_at": block.updated_at,
    }
