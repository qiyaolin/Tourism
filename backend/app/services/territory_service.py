import math
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.poi import Poi
from app.models.poi_correction import PoiCorrection
from app.models.territory import (
    TerritoryGuardian,
    TerritoryGuardianActivityLog,
    TerritoryGuardianApplication,
    TerritoryGuardianReputationSnapshot,
    TerritoryRegion,
)
from app.models.user import User
from app.schemas.territory import (
    TerritoryGuardianApplicationCreatePayload,
    TerritoryGuardianApplicationListResponse,
    TerritoryGuardianApplicationResponse,
    TerritoryGuardianBrief,
    TerritoryGuardianCheckInResponse,
    TerritoryGuardianReputationItem,
    TerritoryGuardianReputationListResponse,
    TerritoryGuardianResumeResponse,
    TerritoryRebuildResponse,
    TerritoryRegionItem,
    TerritoryRegionListResponse,
)

settings = get_settings()


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
                state=guardian.state,
                granted_at=guardian.granted_at,
            )
        )
    return result


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


def list_territories(db: Session) -> TerritoryRegionListResponse:
    evaluate_guardian_governance(db)
    rows = db.execute(
        select(TerritoryRegion, func.ST_AsText(TerritoryRegion.boundary_geom), func.ST_AsText(TerritoryRegion.centroid_geom))
        .where(TerritoryRegion.status == "active")
        .order_by(TerritoryRegion.poi_count.desc(), TerritoryRegion.created_at.asc())
    ).all()
    territory_ids = [region.id for region, _, _ in rows]
    guardian_map = _guardian_rows_to_map(db, territory_ids)
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
    return TerritoryRegionItem(
        id=region.id,
        code=region.code,
        name=region.name,
        status=region.status,
        poi_count=region.poi_count,
        boundary_wkt=boundary_wkt or "",
        centroid_wkt=centroid_wkt or "",
        guardians=guardian_map.get(region.id, []),
    )


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
    return territory_id in set(active_guardian_territory_ids(db, user.id))


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
            TerritoryGuardian.state.in_(("active", "honorary")),
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
    db.commit()
    return TerritoryGuardianCheckInResponse(
        territory_id=territory_id,
        guardian_user_id=current_user.id,
        checked_in_at=now,
    )


def evaluate_guardian_governance(db: Session) -> None:
    now = datetime.now(UTC)
    activity_cutoff = now - timedelta(days=settings.guardian_active_window_days)
    review_window_size = settings.guardian_reputation_window
    review_threshold = settings.guardian_reputation_threshold

    guardians = db.scalars(
        select(TerritoryGuardian).where(TerritoryGuardian.revoked_at.is_(None))
    ).all()
    for guardian in guardians:
        review_statuses = list(
            db.scalars(
                select(PoiCorrection.status)
                .join(Poi, Poi.id == PoiCorrection.poi_id)
                .where(
                    PoiCorrection.reviewer_user_id == guardian.user_id,
                    PoiCorrection.reviewed_at.is_not(None),
                    Poi.territory_id == guardian.territory_id,
                )
                .order_by(PoiCorrection.reviewed_at.desc())
                .limit(review_window_size)
            ).all()
        )
        reviewed_count = len(review_statuses)
        accepted_count = sum(1 for item in review_statuses if item == "accepted")
        accuracy = float(accepted_count / reviewed_count) if reviewed_count > 0 else 1.0
        snapshot_status = (
            "suspended"
            if reviewed_count >= review_window_size and accuracy < review_threshold
            else "ok"
        )
        snapshot = db.scalars(
            select(TerritoryGuardianReputationSnapshot).where(
                TerritoryGuardianReputationSnapshot.territory_id == guardian.territory_id,
                TerritoryGuardianReputationSnapshot.guardian_user_id == guardian.user_id,
            )
        ).first()
        if snapshot is None:
            snapshot = TerritoryGuardianReputationSnapshot(
                territory_id=guardian.territory_id,
                guardian_user_id=guardian.user_id,
                window_size=review_window_size,
                reviewed_count=reviewed_count,
                accepted_count=accepted_count,
                accuracy=accuracy,
                status=snapshot_status,
                calculated_at=now,
            )
        else:
            snapshot.window_size = review_window_size
            snapshot.reviewed_count = reviewed_count
            snapshot.accepted_count = accepted_count
            snapshot.accuracy = accuracy
            snapshot.status = snapshot_status
            snapshot.calculated_at = now
        db.add(snapshot)

        if snapshot_status == "suspended" and guardian.state != "suspended":
            guardian.state = "suspended"
            db.add(guardian)

        if guardian.state in {"active", "honorary"}:
            last_activity = db.scalar(
                select(func.max(TerritoryGuardianActivityLog.created_at)).where(
                    TerritoryGuardianActivityLog.guardian_user_id == guardian.user_id,
                    TerritoryGuardianActivityLog.territory_id == guardian.territory_id,
                    TerritoryGuardianActivityLog.action_type.in_(("check_in", "review")),
                )
            )
            if last_activity is None or last_activity < activity_cutoff:
                if guardian.state == "active":
                    guardian.state = "honorary"
                    db.add(guardian)
            elif guardian.state == "honorary":
                guardian.state = "active"
                db.add(guardian)
    db.commit()


def list_guardian_reputation(db: Session) -> TerritoryGuardianReputationListResponse:
    evaluate_guardian_governance(db)
    rows = db.execute(
        select(
            TerritoryGuardianReputationSnapshot,
            TerritoryGuardian,
            TerritoryRegion.name,
            User.nickname,
        )
        .join(
            TerritoryGuardian,
            (TerritoryGuardian.territory_id == TerritoryGuardianReputationSnapshot.territory_id)
            & (TerritoryGuardian.user_id == TerritoryGuardianReputationSnapshot.guardian_user_id),
        )
        .join(TerritoryRegion, TerritoryRegion.id == TerritoryGuardianReputationSnapshot.territory_id)
        .join(User, User.id == TerritoryGuardianReputationSnapshot.guardian_user_id)
        .order_by(
            TerritoryGuardianReputationSnapshot.status.desc(),
            TerritoryGuardianReputationSnapshot.accuracy.asc(),
            TerritoryGuardianReputationSnapshot.calculated_at.desc(),
        )
    ).all()
    items = [
        TerritoryGuardianReputationItem(
            guardian_id=guardian.id,
            territory_id=snapshot.territory_id,
            territory_name=territory_name,
            guardian_user_id=snapshot.guardian_user_id,
            guardian_nickname=nickname,
            guardian_state=guardian.state,
            reviewed_count=snapshot.reviewed_count,
            accepted_count=snapshot.accepted_count,
            accuracy=snapshot.accuracy,
            threshold=settings.guardian_reputation_threshold,
            status=snapshot.status,
            calculated_at=snapshot.calculated_at,
        )
        for snapshot, guardian, territory_name, nickname in rows
    ]
    return TerritoryGuardianReputationListResponse(items=items)


def resume_guardian(
    db: Session,
    guardian_id: UUID,
) -> TerritoryGuardianResumeResponse:
    guardian = db.get(TerritoryGuardian, guardian_id)
    if guardian is None or guardian.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guardian not found")
    guardian.state = "active"
    guardian.updated_at = datetime.now(UTC)
    db.add(guardian)
    db.commit()
    db.refresh(guardian)
    return TerritoryGuardianResumeResponse(
        guardian_id=guardian.id,
        territory_id=guardian.territory_id,
        state=guardian.state,
        updated_at=guardian.updated_at,
    )
