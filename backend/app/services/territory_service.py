import math
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.bounty import BountyTask
from app.models.poi import Poi
from app.models.poi_correction import PoiCorrection
from app.models.territory import (
    TerritoryGuardian,
    TerritoryGuardianActivityLog,
    TerritoryGuardianApplication,
    TerritoryRegion,
)
from app.models.user import User
from app.schemas.territory import (
    TaskCenterItem,
    TaskCenterResponse,
    TerritoryGuardianApplicationCreatePayload,
    TerritoryGuardianApplicationListResponse,
    TerritoryGuardianApplicationResponse,
    TerritoryGuardianBrief,
    TerritoryGuardianCheckInResponse,
    TerritoryOpportunityResponse,
    TerritoryRebuildResponse,
    TerritoryRegionItem,
    TerritoryRegionListResponse,
    UserTerritoryProfileResponse,
    UserTerritoryRoleItem,
)

settings = get_settings()

# ---------------------------------------------------------------------------
# Role hierarchy (lowest 鈫?highest)
# ---------------------------------------------------------------------------

ROLE_HIERARCHY = ["regular", "local_expert", "area_guide", "city_ambassador"]

ROLE_LABELS = {
    "regular": "甯稿",
    "local_expert": "鍦ㄥ湴杈句汉",
    "area_guide": "鍖哄煙鍚戝",
    "city_ambassador": "鍩庡競澶т娇",
}


def _next_role(current: str) -> str | None:
    try:
        idx = ROLE_HIERARCHY.index(current)
    except ValueError:
        return None
    if idx + 1 < len(ROLE_HIERARCHY):
        return ROLE_HIERARCHY[idx + 1]
    return None


def _role_index(role: str) -> int:
    try:
        return ROLE_HIERARCHY.index(role)
    except ValueError:
        return 0


# ---------------------------------------------------------------------------
# Geometry helpers (unchanged)
# ---------------------------------------------------------------------------


def _parse_point_text(raw: str) -> tuple[float, float]:
    cleaned = raw.strip()
    if cleaned.startswith("POINT(") and cleaned.endswith(")"):
        cleaned = cleaned[len("POINT(") : -1]
    lon_str, lat_str = cleaned.split(" ", maxsplit=1)
    return float(lon_str), float(lat_str)


def _point_text(longitude: float, latitude: float) -> str:
    return f"POINT({longitude:.8f} {latitude:.8f})"


def _polygon_for_cell(cell_x: int, cell_y: int, grid_size: float) -> str:
    min_lon = cell_x * grid_size
    min_lat = cell_y * grid_size
    max_lon = min_lon + grid_size
    max_lat = min_lat + grid_size
    return (
        "POLYGON(("
        f"{min_lon:.8f} {min_lat:.8f},"
        f"{max_lon:.8f} {min_lat:.8f},"
        f"{max_lon:.8f} {max_lat:.8f},"
        f"{min_lon:.8f} {max_lat:.8f},"
        f"{min_lon:.8f} {min_lat:.8f}"
        "))"
    )


def _cell_for_point(longitude: float, latitude: float, grid_size: float) -> tuple[int, int]:
    return int(math.floor(longitude / grid_size)), int(math.floor(latitude / grid_size))


# ---------------------------------------------------------------------------
# Guardian helpers
# ---------------------------------------------------------------------------


def _guardian_rows_to_map(
    db: Session,
    territory_ids: Iterable[UUID],
) -> dict[UUID, list[TerritoryGuardianBrief]]:
    ids = [item for item in territory_ids]
    if not ids:
        return {}
    guardian_rows = db.execute(
        select(TerritoryGuardian, User.nickname)
        .join(User, User.id == TerritoryGuardian.user_id)
        .where(TerritoryGuardian.territory_id.in_(ids), TerritoryGuardian.revoked_at.is_(None))
        .order_by(TerritoryGuardian.granted_at.asc())
    ).all()
    result: dict[UUID, list[TerritoryGuardianBrief]] = {}
    for guardian, nickname in guardian_rows:
        result.setdefault(guardian.territory_id, []).append(
            TerritoryGuardianBrief(
                user_id=guardian.user_id,
                nickname=nickname,
                role=guardian.role,
                state=guardian.state,
                granted_at=guardian.granted_at,
            )
        )
    return result


# ---------------------------------------------------------------------------
# Territory region CRUD
# ---------------------------------------------------------------------------


def rebuild_territory_regions(db: Session) -> TerritoryRebuildResponse:
    grid_size = settings.territory_grid_size_deg
    min_pois = settings.territory_min_pois
    if grid_size <= 0:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid territory grid size")
    if min_pois <= 0:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid territory min_pois")

    poi_rows = db.execute(select(Poi.id, func.ST_AsText(Poi.geom))).all()
    buckets: dict[tuple[int, int], list[UUID]] = {}
    for poi_id, poi_wkt in poi_rows:
        if not poi_wkt:
            continue
        lon, lat = _parse_point_text(poi_wkt)
        cell = _cell_for_point(lon, lat, grid_size)
        buckets.setdefault(cell, []).append(poi_id)

    existing_regions = db.scalars(select(TerritoryRegion)).all()
    region_by_code = {region.code: region for region in existing_regions}

    selected_cells = [(cell, poi_ids) for cell, poi_ids in buckets.items() if len(poi_ids) >= min_pois]
    selected_cells.sort(key=lambda item: len(item[1]), reverse=True)

    active_codes: set[str] = set()
    assigned_poi_ids: list[UUID] = []
    generated_regions = 0
    for index, (cell, poi_ids) in enumerate(selected_cells, start=1):
        cell_x, cell_y = cell
        code = f"cell_{cell_x}_{cell_y}"
        active_codes.add(code)
        region = region_by_code.get(code)
        if region is None:
            generated_regions += 1
            region = TerritoryRegion(
                id=uuid.uuid4(),
                code=code,
                name=f"{settings.territory_region_name_prefix}{index:03d}",
                status="active",
                boundary_geom=_polygon_for_cell(cell_x, cell_y, grid_size),
                centroid_geom=_point_text((cell_x + 0.5) * grid_size, (cell_y + 0.5) * grid_size),
                poi_count=len(poi_ids),
            )
            db.add(region)
            db.flush()
            region_by_code[code] = region
        else:
            region.status = "active"
            region.poi_count = len(poi_ids)
            region.boundary_geom = _polygon_for_cell(cell_x, cell_y, grid_size)
            region.centroid_geom = _point_text((cell_x + 0.5) * grid_size, (cell_y + 0.5) * grid_size)
            db.add(region)

        db.execute(update(Poi).where(Poi.id.in_(poi_ids)).values(territory_id=region.id))
        assigned_poi_ids.extend(poi_ids)

    if assigned_poi_ids:
        db.execute(update(Poi).where(~Poi.id.in_(assigned_poi_ids)).values(territory_id=None))
    else:
        db.execute(update(Poi).values(territory_id=None))

    inactive_regions = 0
    for region in existing_regions:
        if region.code in active_codes:
            continue
        if region.status != "inactive" or region.poi_count != 0:
            region.status = "inactive"
            region.poi_count = 0
            db.add(region)
            inactive_regions += 1

    db.commit()
    return TerritoryRebuildResponse(
        generated_regions=generated_regions,
        assigned_pois=len(assigned_poi_ids),
        inactive_regions=inactive_regions,
    )


def _bootstrap_territories_if_needed(db: Session) -> None:
    active_count = db.scalar(
        select(func.count()).select_from(TerritoryRegion).where(TerritoryRegion.status == "active")
    ) or 0
    if active_count > 0:
        return
    poi_count = db.scalar(select(func.count()).select_from(Poi)) or 0
    if poi_count < settings.territory_min_pois:
        return
    rebuild_territory_regions(db)


def list_territories(db: Session) -> TerritoryRegionListResponse:
    _bootstrap_territories_if_needed(db)
    evaluate_guardian_governance(db)
    rows = db.execute(
        select(TerritoryRegion, func.ST_AsText(TerritoryRegion.boundary_geom), func.ST_AsText(TerritoryRegion.centroid_geom))
        .where(TerritoryRegion.status == "active")
        .order_by(TerritoryRegion.poi_count.desc(), TerritoryRegion.created_at.asc())
    ).all()
    territory_ids = [region.id for region, _, _ in rows]
    guardian_map = _guardian_rows_to_map(db, territory_ids)

    # Fetch sample POIs
    ranked_pois_subq = (
        select(
            Poi.territory_id,
            Poi.name,
            func.row_number().over(
                partition_by=Poi.territory_id,
                order_by=Poi.updated_at.desc()
            ).label('rn')
        )
        .where(Poi.territory_id.in_(territory_ids))
        .subquery()
    )
    
    sample_pois_query = db.execute(
        select(ranked_pois_subq.c.territory_id, ranked_pois_subq.c.name)
        .where(ranked_pois_subq.c.rn <= 3)
    ).all()
    
    samples_by_region: dict[UUID, list[str]] = {rid: [] for rid in territory_ids}
    for territory_id, name in sample_pois_query:
        if territory_id:
            samples_by_region[territory_id].append(name)

    items = [
        TerritoryRegionItem(
            id=region.id,
            code=region.code,
            name=region.name,
            status=region.status,
            poi_count=region.poi_count,
            boundary_wkt=boundary_wkt or "",
            centroid_wkt=centroid_wkt or "",
            guardians=guardian_map.get(region.id, []),
            sample_pois=samples_by_region.get(region.id, [])
        )
        for region, boundary_wkt, centroid_wkt in rows
    ]
    return TerritoryRegionListResponse(items=items)


def get_territory(db: Session, territory_id: UUID) -> TerritoryRegionItem:
    evaluate_guardian_governance(db)
    row = db.execute(
        select(TerritoryRegion, func.ST_AsText(TerritoryRegion.boundary_geom), func.ST_AsText(TerritoryRegion.centroid_geom))
        .where(TerritoryRegion.id == territory_id)
        .limit(1)
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Territory not found")
    region, boundary_wkt, centroid_wkt = row
    guardian_map = _guardian_rows_to_map(db, [region.id])
    
    sample_pois = db.scalars(
        select(Poi.name)
        .where(Poi.territory_id == territory_id)
        .order_by(Poi.updated_at.desc())
        .limit(3)
    ).all()

    return TerritoryRegionItem(
        id=region.id,
        code=region.code,
        name=region.name,
        status=region.status,
        poi_count=region.poi_count,
        boundary_wkt=boundary_wkt or "",
        centroid_wkt=centroid_wkt or "",
        guardians=guardian_map.get(region.id, []),
        sample_pois=list(sample_pois)
    )


# ---------------------------------------------------------------------------
# Legacy: guardian applications (kept for backward compat)
# ---------------------------------------------------------------------------


def submit_guardian_application(
    db: Session,
    payload: TerritoryGuardianApplicationCreatePayload,
    current_user: User,
) -> TerritoryGuardianApplicationResponse:
    territory = db.get(TerritoryRegion, payload.territory_id)
    if territory is None or territory.status != "active":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Territory not found")
    existing_guardian = db.scalars(
        select(TerritoryGuardian).where(
            TerritoryGuardian.territory_id == payload.territory_id,
            TerritoryGuardian.user_id == current_user.id,
            TerritoryGuardian.revoked_at.is_(None),
        )
    ).first()
    if existing_guardian is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already a guardian for this territory")
    existing_pending = db.scalars(
        select(TerritoryGuardianApplication).where(
            TerritoryGuardianApplication.territory_id == payload.territory_id,
            TerritoryGuardianApplication.applicant_user_id == current_user.id,
            TerritoryGuardianApplication.status == "pending",
        )
    ).first()
    if existing_pending is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pending application already exists")

    row = TerritoryGuardianApplication(
        territory_id=payload.territory_id,
        applicant_user_id=current_user.id,
        reason=payload.reason.strip() if payload.reason else None,
        status="pending",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return TerritoryGuardianApplicationResponse(
        id=row.id,
        territory_id=row.territory_id,
        territory_name=territory.name,
        applicant_user_id=row.applicant_user_id,
        applicant_nickname=current_user.nickname,
        reason=row.reason,
        status=row.status,
        reviewer_user_id=None,
        reviewer_nickname=None,
        review_comment=None,
        reviewed_at=None,
        created_at=row.created_at,
    )


def _application_to_response(
    row: TerritoryGuardianApplication,
    territory_name: str,
    applicant_nickname: str,
    reviewer_nickname: str | None,
) -> TerritoryGuardianApplicationResponse:
    return TerritoryGuardianApplicationResponse(
        id=row.id,
        territory_id=row.territory_id,
        territory_name=territory_name,
        applicant_user_id=row.applicant_user_id,
        applicant_nickname=applicant_nickname,
        reason=row.reason,
        status=row.status,
        reviewer_user_id=row.reviewer_user_id,
        reviewer_nickname=reviewer_nickname,
        review_comment=row.review_comment,
        reviewed_at=row.reviewed_at,
        created_at=row.created_at,
    )


def list_guardian_applications(
    db: Session,
    status_filter: str,
    offset: int,
    limit: int,
) -> TerritoryGuardianApplicationListResponse:
    filters = []
    if status_filter != "all":
        filters.append(TerritoryGuardianApplication.status == status_filter)
    base_query = select(TerritoryGuardianApplication).where(*filters)
    total = db.scalar(select(func.count()).select_from(base_query.subquery())) or 0
    rows = db.scalars(
        base_query.order_by(TerritoryGuardianApplication.created_at.desc()).offset(offset).limit(limit)
    ).all()
    if not rows:
        return TerritoryGuardianApplicationListResponse(items=[], total=0, offset=offset, limit=limit)

    territory_map = {
        item.id: item.name
        for item in db.scalars(
            select(TerritoryRegion).where(TerritoryRegion.id.in_({row.territory_id for row in rows}))
        ).all()
    }
    user_ids = {row.applicant_user_id for row in rows}
    user_ids.update({row.reviewer_user_id for row in rows if row.reviewer_user_id is not None})
    user_map = {item.id: item.nickname for item in db.scalars(select(User).where(User.id.in_(user_ids))).all()}
    items = [
        _application_to_response(
            row=row,
            territory_name=territory_map.get(row.territory_id, ""),
            applicant_nickname=user_map.get(row.applicant_user_id, ""),
            reviewer_nickname=user_map.get(row.reviewer_user_id) if row.reviewer_user_id else None,
        )
        for row in rows
    ]
    return TerritoryGuardianApplicationListResponse(items=items, total=total, offset=offset, limit=limit)


def review_guardian_application(
    db: Session,
    application_id: UUID,
    action: str,
    review_comment: str | None,
    current_user: User,
) -> TerritoryGuardianApplicationResponse:
    row = db.scalars(
        select(TerritoryGuardianApplication)
        .where(TerritoryGuardianApplication.id == application_id)
        .with_for_update()
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if row.status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Application already reviewed")

    territory = db.get(TerritoryRegion, row.territory_id)
    if territory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Territory not found")

    row.status = "approved" if action == "approve" else "rejected"
    row.review_comment = review_comment.strip() if review_comment else None
    row.reviewer_user_id = current_user.id
    row.reviewed_at = datetime.now(UTC)
    db.add(row)

    if action == "approve":
        guardian = db.scalars(
            select(TerritoryGuardian).where(
                TerritoryGuardian.territory_id == row.territory_id,
                TerritoryGuardian.user_id == row.applicant_user_id,
            )
        ).first()
        if guardian is None:
            guardian = TerritoryGuardian(
                territory_id=row.territory_id,
                user_id=row.applicant_user_id,
                role="regular",
                state="active",
                granted_by_user_id=current_user.id,
            )
        else:
            guardian.state = "active"
            guardian.revoked_at = None
            guardian.revoked_by_user_id = None
            guardian.granted_by_user_id = current_user.id
        db.add(guardian)

    db.commit()
    db.refresh(row)

    applicant = db.get(User, row.applicant_user_id)
    reviewer = db.get(User, row.reviewer_user_id) if row.reviewer_user_id else None
    return _application_to_response(
        row=row,
        territory_name=territory.name,
        applicant_nickname=applicant.nickname if applicant else "",
        reviewer_nickname=reviewer.nickname if reviewer else None,
    )


# ---------------------------------------------------------------------------
# Guardian territory membership helpers
# ---------------------------------------------------------------------------


def active_guardian_territory_ids(db: Session, user_id: UUID) -> list[UUID]:
    return list(
        db.scalars(
            select(TerritoryGuardian.territory_id).where(
                TerritoryGuardian.user_id == user_id,
                TerritoryGuardian.state == "active",
                TerritoryGuardian.revoked_at.is_(None),
            )
        ).all()
    )


def can_review_correction_in_territory(db: Session, user: User, territory_id: UUID | None) -> bool:
    if user.role == "admin":
        return True
    if territory_id is None:
        return True
    # Only area_guide and city_ambassador can review corrections
    guardian = db.scalars(
        select(TerritoryGuardian).where(
            TerritoryGuardian.user_id == user.id,
            TerritoryGuardian.territory_id == territory_id,
            TerritoryGuardian.state == "active",
            TerritoryGuardian.revoked_at.is_(None),
            TerritoryGuardian.role.in_(("area_guide", "city_ambassador")),
        )
    ).first()
    return guardian is not None


def user_role_in_territory(db: Session, user_id: UUID, territory_id: UUID | None) -> str | None:
    """Return the user's role in the given territory, or None if not a guardian."""
    if territory_id is None:
        return None
    guardian = db.scalars(
        select(TerritoryGuardian).where(
            TerritoryGuardian.user_id == user_id,
            TerritoryGuardian.territory_id == territory_id,
            TerritoryGuardian.revoked_at.is_(None),
        )
    ).first()
    return guardian.role if guardian else None


# ---------------------------------------------------------------------------
# Activity logging
# ---------------------------------------------------------------------------


def log_guardian_review_activity(
    db: Session,
    guardian_user_id: UUID,
    territory_id: UUID,
    correction_id: UUID,
) -> None:
    db.add(
        TerritoryGuardianActivityLog(
            territory_id=territory_id,
            guardian_user_id=guardian_user_id,
            action_type="review",
            related_correction_id=correction_id,
            payload=None,
        )
    )
    _touch_guardian_active(db, guardian_user_id, territory_id)


def guardian_check_in(
    db: Session,
    territory_id: UUID,
    current_user: User,
) -> TerritoryGuardianCheckInResponse:
    guardian = db.scalars(
        select(TerritoryGuardian).where(
            TerritoryGuardian.territory_id == territory_id,
            TerritoryGuardian.user_id == current_user.id,
            TerritoryGuardian.revoked_at.is_(None),
        )
    ).first()
    if guardian is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a guardian of this territory")
    now = datetime.now(UTC)
    db.add(
        TerritoryGuardianActivityLog(
            territory_id=territory_id,
            guardian_user_id=current_user.id,
            action_type="check_in",
            payload=None,
            created_at=now,
        )
    )
    _touch_guardian_active(db, current_user.id, territory_id)
    db.commit()
    return TerritoryGuardianCheckInResponse(
        territory_id=territory_id,
        guardian_user_id=current_user.id,
        checked_in_at=now,
    )


def _touch_guardian_active(db: Session, user_id: UUID, territory_id: UUID) -> None:
    """Update last_active_at and restore dormant guardians to active."""
    guardian = db.scalars(
        select(TerritoryGuardian).where(
            TerritoryGuardian.user_id == user_id,
            TerritoryGuardian.territory_id == territory_id,
            TerritoryGuardian.revoked_at.is_(None),
        )
    ).first()
    if guardian is None:
        return
    now = datetime.now(UTC)
    guardian.last_active_at = now
    # Auto-recover from dormancy when user becomes active again
    if guardian.state == "dormant":
        guardian.state = "active"
    db.add(guardian)


# ---------------------------------------------------------------------------
# Role evaluation & auto-promotion (core of the optimisation)
# ---------------------------------------------------------------------------


def _compute_target_role(
    contribution_count: int,
    thanks_received: int,
    account_age_days: int,
    area_count: int,
) -> str:
    """
    Compute the target role based on contribution metrics.
    Roles never demote 鈥?we always return the highest eligible role.
    """
    if (
        area_count >= settings.role_ambassador_min_areas
        and thanks_received >= settings.role_guide_min_thanks
        and contribution_count >= settings.role_expert_min_contributions
        and account_age_days >= settings.role_expert_min_age_days
    ):
        return "city_ambassador"
    if (
        thanks_received >= settings.role_guide_min_thanks
        and contribution_count >= settings.role_expert_min_contributions
        and account_age_days >= settings.role_expert_min_age_days
    ):
        return "area_guide"
    if (
        contribution_count >= settings.role_expert_min_contributions
        and account_age_days >= settings.role_expert_min_age_days
    ):
        return "local_expert"
    if contribution_count >= settings.role_regular_min_contributions:
        return "regular"
    return "regular"  # base role once guardian record exists


def evaluate_user_territory_role(
    db: Session,
    user_id: UUID,
    territory_id: UUID,
) -> TerritoryGuardian:
    """
    Evaluate and potentially promote a user's role in a territory.
    Creates the guardian record if it doesn't exist yet.
    Roles never demote.
    """
    guardian = db.scalars(
        select(TerritoryGuardian).where(
            TerritoryGuardian.user_id == user_id,
            TerritoryGuardian.territory_id == territory_id,
            TerritoryGuardian.revoked_at.is_(None),
        )
    ).first()

    if guardian is None:
        guardian = TerritoryGuardian(
            territory_id=territory_id,
            user_id=user_id,
            role="regular",
            state="active",
            contribution_count=0,
            thanks_received=0,
            last_active_at=datetime.now(UTC),
        )
        db.add(guardian)
        db.flush()

    # Calculate account age
    user = db.get(User, user_id)
    account_age_days = 0
    if user and user.created_at:
        account_age_days = (datetime.now(UTC) - user.created_at.replace(tzinfo=UTC if user.created_at.tzinfo is None else user.created_at.tzinfo)).days

    # Count distinct territories where user is a guardian
    area_count = db.scalar(
        select(func.count(func.distinct(TerritoryGuardian.territory_id))).where(
            TerritoryGuardian.user_id == user_id,
            TerritoryGuardian.revoked_at.is_(None),
            TerritoryGuardian.role.in_(("area_guide", "city_ambassador")),
        )
    ) or 0

    target_role = _compute_target_role(
        contribution_count=guardian.contribution_count,
        thanks_received=guardian.thanks_received,
        account_age_days=account_age_days,
        area_count=area_count,
    )

    # Never demote: only promote if target is higher
    if _role_index(target_role) > _role_index(guardian.role):
        guardian.role = target_role
        db.add(guardian)

    return guardian


def record_territory_contribution(
    db: Session,
    user_id: UUID,
    territory_id: UUID,
    action_type: str,
    related_correction_id: UUID | None = None,
) -> TerritoryGuardian:
    """
    Record a contribution, increment counters, and evaluate role promotion.
    This is the main entry point for the unified contribution system.
    """
    # Ensure guardian record exists
    guardian = db.scalars(
        select(TerritoryGuardian).where(
            TerritoryGuardian.user_id == user_id,
            TerritoryGuardian.territory_id == territory_id,
            TerritoryGuardian.revoked_at.is_(None),
        )
    ).first()

    now = datetime.now(UTC)
    if guardian is None:
        guardian = TerritoryGuardian(
            territory_id=territory_id,
            user_id=user_id,
            role="regular",
            state="active",
            contribution_count=0,
            thanks_received=0,
            last_active_at=now,
        )
        db.add(guardian)
        db.flush()

    # Log the activity
    db.add(
        TerritoryGuardianActivityLog(
            territory_id=territory_id,
            guardian_user_id=user_id,
            action_type=action_type,
            related_correction_id=related_correction_id,
            payload=None,
            created_at=now,
        )
    )

    # Update counters
    guardian.contribution_count += 1
    guardian.last_active_at = now
    if guardian.state == "dormant":
        guardian.state = "active"
    db.add(guardian)

    # Evaluate role promotion
    return evaluate_user_territory_role(db, user_id, territory_id)


# ---------------------------------------------------------------------------
# Governance: natural decay (replaces punitive system)
# ---------------------------------------------------------------------------


def evaluate_guardian_governance(db: Session) -> None:
    """
    Evaluate all guardians and apply natural decay.
    - 90-day sliding window: guardians inactive beyond window become 'dormant'
    - Dormant guardians keep their role 鈥?state simply turns grey
    - Active guardians who were dormant auto-recover via _touch_guardian_active
    """
    now = datetime.now(UTC)
    dormant_cutoff = now - timedelta(days=settings.guardian_dormant_window_days)

    guardians = db.scalars(
        select(TerritoryGuardian).where(TerritoryGuardian.revoked_at.is_(None))
    ).all()
    for guardian in guardians:
        effective_last_active = guardian.last_active_at or guardian.granted_at
        if effective_last_active < dormant_cutoff:
            if guardian.state == "active":
                guardian.state = "dormant"
                db.add(guardian)
        elif guardian.state == "dormant":
            # Auto-recover if last_active_at is within window
            guardian.state = "active"
            db.add(guardian)
    db.commit()


# ---------------------------------------------------------------------------
# User profile & task center (new endpoints)
# ---------------------------------------------------------------------------


def _compute_next_role_progress(guardian: TerritoryGuardian, account_age_days: int) -> float:
    """Compute progress toward the next role as a float 0.0 ~ 1.0."""
    nr = _next_role(guardian.role)
    if nr is None:
        return 1.0

    if nr == "local_expert":
        contrib_progress = min(guardian.contribution_count / max(settings.role_expert_min_contributions, 1), 1.0)
        age_progress = min(account_age_days / max(settings.role_expert_min_age_days, 1), 1.0)
        return (contrib_progress + age_progress) / 2.0
    elif nr == "area_guide":
        return min(guardian.thanks_received / max(settings.role_guide_min_thanks, 1), 1.0)
    elif nr == "city_ambassador":
        return 0.0  # Needs multi-area coverage, computed at higher level
    return 0.0


def get_user_territory_profile(db: Session, user_id: UUID) -> UserTerritoryProfileResponse:
    """Return the user's territory roles, contribution stats, and promotion progress."""
    guardians = db.scalars(
        select(TerritoryGuardian).where(
            TerritoryGuardian.user_id == user_id,
            TerritoryGuardian.revoked_at.is_(None),
        ).order_by(TerritoryGuardian.contribution_count.desc())
    ).all()

    territory_ids = [g.territory_id for g in guardians]
    territory_map: dict[UUID, str] = {}
    if territory_ids:
        for t in db.scalars(select(TerritoryRegion).where(TerritoryRegion.id.in_(territory_ids))).all():
            territory_map[t.id] = t.name

    user = db.get(User, user_id)
    account_age_days = 0
    if user and user.created_at:
        account_age_days = (datetime.now(UTC) - user.created_at.replace(tzinfo=UTC if user.created_at.tzinfo is None else user.created_at.tzinfo)).days

    roles = []
    total_contributions = 0
    total_thanks = 0
    for g in guardians:
        total_contributions += g.contribution_count
        total_thanks += g.thanks_received
        nr = _next_role(g.role)
        progress = _compute_next_role_progress(g, account_age_days)
        roles.append(
            UserTerritoryRoleItem(
                territory_id=g.territory_id,
                territory_name=territory_map.get(g.territory_id, ""),
                role=g.role,
                state=g.state,
                contribution_count=g.contribution_count,
                thanks_received=g.thanks_received,
                next_role=nr,
                next_role_progress=round(progress, 2),
            )
        )

    return UserTerritoryProfileResponse(
        user_id=user_id,
        roles=roles,
        total_contributions=total_contributions,
        total_thanks=total_thanks,
    )


def get_task_center(db: Session, user_id: UUID) -> TaskCenterResponse:
    """Return aggregated tasks for the user's guardian territories."""
    guardian_territories = db.execute(
        select(TerritoryGuardian.territory_id, TerritoryGuardian.role, TerritoryRegion.name)
        .join(TerritoryRegion, TerritoryRegion.id == TerritoryGuardian.territory_id)
        .where(
            TerritoryGuardian.user_id == user_id,
            TerritoryGuardian.revoked_at.is_(None),
            TerritoryGuardian.state == "active",
        )
    ).all()

    if not guardian_territories:
        return TaskCenterResponse(
            pending_reviews=0,
            items=[],
            monthly_contributions=0,
            monthly_helped_count=0,
        )

    territory_ids = [t_id for t_id, _, _ in guardian_territories]
    territory_name_map = {t_id: name for t_id, _, name in guardian_territories}
    guide_territory_ids = [t_id for t_id, role, _ in guardian_territories if role in ("area_guide", "city_ambassador")]

    items: list[TaskCenterItem] = []

    # 1. Pending corrections to review (only for area_guide+)
    if guide_territory_ids:
        pending_rows = db.execute(
            select(PoiCorrection.id, PoiCorrection.created_at, Poi.name, Poi.territory_id)
            .join(Poi, Poi.id == PoiCorrection.poi_id)
            .where(
                PoiCorrection.status == "pending",
                Poi.territory_id.in_(guide_territory_ids),
            )
            .order_by(PoiCorrection.created_at.asc())
            .limit(20)
        ).all()
        for corr_id, created_at, poi_name, t_id in pending_rows:
            items.append(
                TaskCenterItem(
                    task_type="pending_review",
                    title=f"审核纠错：{poi_name}",
                    territory_name=territory_name_map.get(t_id, ""),
                    territory_id=t_id,
                    target_id=corr_id,
                    points=10,
                    created_at=created_at,
                )
            )

    # 2. POIs needing verification (any guardian)
    stale_cutoff = datetime.now(UTC) - timedelta(days=45)
    stale_pois = db.execute(
        select(Poi.id, Poi.name, Poi.territory_id, Poi.updated_at)
        .where(
            Poi.territory_id.in_(territory_ids),
            Poi.updated_at < stale_cutoff,
        )
        .order_by(Poi.updated_at.asc())
        .limit(10)
    ).all()
    for poi_id, poi_name, t_id, updated_at in stale_pois:
        items.append(
            TaskCenterItem(
                task_type="poi_verification",
                title=f"验证信息：{poi_name}",
                territory_name=territory_name_map.get(t_id, ""),
                territory_id=t_id,
                target_id=poi_id,
                points=15,
                created_at=updated_at,
            )
        )

    # 3. Open bounty tasks in guardian territories
    bounty_rows = db.execute(
        select(BountyTask.id, BountyTask.generated_at, BountyTask.reward_points, Poi.name, BountyTask.territory_id)
        .join(Poi, Poi.id == BountyTask.poi_id)
        .where(BountyTask.territory_id.in_(territory_ids), BountyTask.status == "open")
        .order_by(BountyTask.generated_at.desc())
        .limit(10)
    ).all()
    for bounty_id, generated_at, reward_points, poi_name, territory_id in bounty_rows:
        items.append(
            TaskCenterItem(
                task_type="bounty",
                title=f"悬赏任务：{poi_name}",
                territory_name=territory_name_map.get(territory_id, ""),
                territory_id=territory_id,
                target_id=bounty_id,
                points=reward_points,
                created_at=generated_at,
            )
        )

    # Monthly stats
    month_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_contributions = db.scalar(
        select(func.count()).select_from(TerritoryGuardianActivityLog).where(
            TerritoryGuardianActivityLog.guardian_user_id == user_id,
            TerritoryGuardianActivityLog.created_at >= month_start,
        )
    ) or 0

    # Approximate "helped count" 鈥?how many corrections were accepted in user's territories
    monthly_helped = db.scalar(
        select(func.count()).select_from(PoiCorrection)
        .join(Poi, Poi.id == PoiCorrection.poi_id)
        .where(
            Poi.territory_id.in_(territory_ids),
            PoiCorrection.status == "accepted",
            PoiCorrection.reviewed_at >= month_start,
        )
    ) or 0

    pending_reviews = sum(1 for item in items if item.task_type == "pending_review")

    return TaskCenterResponse(
        pending_reviews=pending_reviews,
        items=items,
        monthly_contributions=monthly_contributions,
        monthly_helped_count=monthly_helped,
    )

def get_territory_opportunities(db: Session, territory_id: UUID) -> TerritoryOpportunityResponse:
    region = db.get(TerritoryRegion, territory_id)
    if not region:
        raise HTTPException(status_code=404, detail="Territory not found")

    items: list[TaskCenterItem] = []

    pending_corrections = db.scalars(
        select(PoiCorrection)
        .join(Poi, Poi.id == PoiCorrection.poi_id)
        .where(
            PoiCorrection.status == "pending",
            Poi.territory_id == territory_id,
        )
        .order_by(PoiCorrection.created_at.desc())
        .limit(3)
    ).all()

    for correction in pending_corrections:
        poi = db.get(Poi, correction.poi_id)
        poi_name = poi.name if poi else "未知地点"
        items.append(
            TaskCenterItem(
                task_type="pending_review",
                title=f"审核纠错：{poi_name}",
                territory_name=region.name,
                territory_id=territory_id,
                target_id=correction.id,
                points=5,
                created_at=correction.created_at,
            )
        )

    pois_missing_info = db.scalars(
        select(Poi)
        .where(
            Poi.territory_id == territory_id,
            Poi.opening_hours.is_(None),
        )
        .order_by(Poi.created_at.desc())
        .limit(4)
    ).all()

    for poi in pois_missing_info:
        items.append(
            TaskCenterItem(
                task_type="nearby_opportunity",
                title=f"补充营业时间：{poi.name}",
                territory_name=region.name,
                territory_id=territory_id,
                target_id=poi.id,
                points=10,
                created_at=poi.created_at,
            )
        )

    bounty_rows = db.execute(
        select(BountyTask.id, BountyTask.generated_at, BountyTask.reward_points, Poi.name)
        .join(Poi, Poi.id == BountyTask.poi_id)
        .where(BountyTask.territory_id == territory_id, BountyTask.status == "open")
        .order_by(BountyTask.generated_at.desc())
        .limit(3)
    ).all()
    for bounty_id, generated_at, reward_points, poi_name in bounty_rows:
        items.append(
            TaskCenterItem(
                task_type="bounty",
                title=f"悬赏任务：{poi_name}",
                territory_name=region.name,
                territory_id=territory_id,
                target_id=bounty_id,
                points=reward_points,
                created_at=generated_at,
            )
        )

    return TerritoryOpportunityResponse(
        territory_id=territory_id,
        items=items,
    )
