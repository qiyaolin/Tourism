import uuid
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.block_template import BlockTemplate, BlockTemplateRating
from app.models.user import User


def publish_template(
    db: Session,
    user_id: uuid.UUID,
    title: str,
    description: str | None,
    style_tags: list[str] | None,
    block_type: str,
    is_group: bool,
    content_snapshot: dict[str, Any] | None,
    children_snapshot: list[dict[str, Any]] | None,
    longitude: float | None,
    latitude: float | None,
    region_name: str | None,
) -> dict[str, Any]:
    """Publish a new template to the community library."""
    template = BlockTemplate(
        author_id=user_id,
        title=title,
        description=description,
        style_tags=style_tags,
        block_type=block_type,
        is_group=is_group,
        content_snapshot=content_snapshot,
        children_snapshot=children_snapshot,
        region_name=region_name,
        status="published",
    )
    db.add(template)
    db.flush()

    if longitude is not None and latitude is not None:
        db.execute(
            text(
                "UPDATE block_templates "
                "SET location_geom = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326) "
                "WHERE id = :id"
            ),
            {"lng": longitude, "lat": latitude, "id": str(template.id)},
        )

    db.commit()
    db.refresh(template)
    return _template_to_dict(db, template)


def list_templates(
    db: Session,
    block_type: str | None = None,
    style_tag: str | None = None,
    region_name: str | None = None,
    search: str | None = None,
    sort_by: str = "hot",
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    """Search/browse the template library."""
    base = select(BlockTemplate).where(BlockTemplate.status == "published")

    if block_type:
        base = base.where(BlockTemplate.block_type == block_type)
    if region_name:
        base = base.where(BlockTemplate.region_name.ilike(f"%{region_name}%"))
    if search:
        base = base.where(BlockTemplate.title.ilike(f"%{search}%"))
    if style_tag:
        # JSON array contains check
        base = base.where(BlockTemplate.style_tags.op("@>")(f'["{style_tag}"]'))

    # Count
    count_stmt = select(func.count()).select_from(base.subquery())
    total = db.execute(count_stmt).scalar() or 0

    # Sort
    if sort_by == "newest":
        base = base.order_by(BlockTemplate.created_at.desc())
    elif sort_by == "rating":
        base = base.order_by(
            (BlockTemplate.rating_sum / func.greatest(BlockTemplate.rating_count, 1)).desc(),
            BlockTemplate.fork_count.desc(),
        )
    else:  # hot
        base = base.order_by(
            (
                BlockTemplate.fork_count * 3
                + BlockTemplate.rating_sum / func.greatest(BlockTemplate.rating_count, 1) * 10
            ).desc(),
            BlockTemplate.created_at.desc(),
        )

    base = base.offset(offset).limit(limit)
    result = db.execute(base)
    rows = result.scalars().all()

    items = []
    for row in rows:
        items.append(_template_to_dict(db, row))

    return items, total


def get_template(db: Session, template_id: uuid.UUID) -> dict[str, Any] | None:
    """Get a single template by ID."""
    stmt = select(BlockTemplate).where(BlockTemplate.id == template_id)
    result = db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return _template_to_dict(db, row)


def fork_template_to_blocks(
    db: Session,
    template_id: uuid.UUID,
    itinerary_id: uuid.UUID,
    day_index: int,
    sort_order: int,
    lane_key: str,
    parent_block_id: uuid.UUID | None,
) -> list[dict[str, Any]]:
    """Fork a template into actual blocks in an itinerary."""
    from app.services.block_service import _row_to_dict

    template = db.get(BlockTemplate, template_id)
    if template is None:
        raise ValueError("Template not found")

    created_blocks: list[dict[str, Any]] = []

    if template.is_group and template.children_snapshot:
        # Create container block
        from app.models.itinerary_block import ItineraryBlock

        container = ItineraryBlock(
            itinerary_id=itinerary_id,
            parent_block_id=parent_block_id,
            sort_order=sort_order,
            day_index=day_index,
            lane_key=lane_key,
            block_type=template.block_type if template.block_type != "group" else "scenic",
            title=template.title,
            is_container=True,
            source_template_id=template_id,
            type_data=template.content_snapshot,
        )
        db.add(container)
        db.flush()
        created_blocks.append(_row_to_dict(container))

        # Create children
        for idx, child_data in enumerate(template.children_snapshot, start=1):
            child = ItineraryBlock(
                itinerary_id=itinerary_id,
                parent_block_id=container.id,
                sort_order=idx,
                day_index=day_index,
                lane_key=lane_key,
                block_type=child_data.get("block_type", "scenic"),
                title=child_data.get("title", ""),
                duration_minutes=child_data.get("duration_minutes"),
                cost=child_data.get("cost"),
                tips=child_data.get("tips"),
                address=child_data.get("address"),
                photos=child_data.get("photos"),
                type_data=child_data.get("type_data"),
                is_container=child_data.get("is_container", False),
                source_template_id=template_id,
            )
            db.add(child)
            db.flush()
            created_blocks.append(_row_to_dict(child))
    else:
        # Single element template
        from app.models.itinerary_block import ItineraryBlock

        snapshot = template.content_snapshot or {}
        block = ItineraryBlock(
            itinerary_id=itinerary_id,
            parent_block_id=parent_block_id,
            sort_order=sort_order,
            day_index=day_index,
            lane_key=lane_key,
            block_type=template.block_type,
            title=template.title,
            duration_minutes=snapshot.get("duration_minutes"),
            cost=snapshot.get("cost"),
            tips=snapshot.get("tips"),
            address=snapshot.get("address"),
            photos=snapshot.get("photos"),
            type_data=snapshot.get("type_data"),
            is_container=snapshot.get("is_container", False),
            source_template_id=template_id,
        )
        db.add(block)
        db.flush()
        created_blocks.append(_row_to_dict(block))

    # Bump fork count
    template.fork_count = template.fork_count + 1
    db.commit()

    return created_blocks


def rate_template(
    db: Session,
    template_id: uuid.UUID,
    user_id: uuid.UUID,
    score: int,
    comment: str | None,
) -> dict[str, Any]:
    """Rate a template (upsert: one rating per user)."""
    template = db.get(BlockTemplate, template_id)
    if template is None:
        raise ValueError("Template not found")

    # Check existing rating
    stmt = select(BlockTemplateRating).where(
        BlockTemplateRating.template_id == template_id,
        BlockTemplateRating.user_id == user_id,
    )
    result = db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        old_score = existing.score
        existing.score = score
        existing.comment = comment
        template.rating_sum = template.rating_sum - old_score + score
    else:
        rating = BlockTemplateRating(
            template_id=template_id,
            user_id=user_id,
            score=score,
            comment=comment,
        )
        db.add(rating)
        template.rating_sum = template.rating_sum + score
        template.rating_count = template.rating_count + 1

    db.commit()
    db.refresh(template)
    return _template_to_dict(db, template)


def _template_to_dict(db: Session, template: BlockTemplate) -> dict[str, Any]:
    """Convert template ORM row to response dict."""
    # Fetch author nickname
    author_nickname = None
    if template.author_id:
        author = db.get(User, template.author_id)
        if author:
            author_nickname = author.nickname

    rating_avg = None
    if template.rating_count > 0:
        rating_avg = round(template.rating_sum / template.rating_count, 2)

    return {
        "id": template.id,
        "author_id": template.author_id,
        "author_nickname": author_nickname,
        "title": template.title,
        "description": template.description,
        "style_tags": template.style_tags,
        "block_type": template.block_type,
        "is_group": template.is_group,
        "content_snapshot": template.content_snapshot,
        "children_snapshot": template.children_snapshot,
        "fork_count": template.fork_count,
        "rating_avg": rating_avg,
        "rating_count": template.rating_count,
        "status": template.status,
        "region_name": template.region_name,
        "created_at": template.created_at,
        "updated_at": template.updated_at,
    }
