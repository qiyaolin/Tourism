import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.passport import BadgeDef, UserBadge, UserContribution

logger = logging.getLogger(__name__)

def record_contribution(
    session: Session,
    user_id: uuid.UUID,
    action_type: str,
    points: int,
    source_id: uuid.UUID | None = None,
) -> UserContribution:
    """
    Record a user contribution and add points.
    Does not run evaluate_badges automatically; caller should do that.
    """
    contribution = UserContribution(
        user_id=user_id,
        action_type=action_type,
        points=points,
        source_id=source_id,
        created_at=datetime.now(UTC)
    )
    session.add(contribution)
    return contribution


def evaluate_badges(session: Session, user_id: uuid.UUID) -> list[UserBadge]:
    """
    Evaluate rules and grant missing badges.
    """
    # 1. Fetch all badges
    all_defs = session.scalars(select(BadgeDef)).all()

    # 2. Fetch user's existing badges
    user_existing_badge_ids = {
        ub.badge_id for ub in session.scalars(select(UserBadge).where(UserBadge.user_id == user_id))
    }

    newly_awarded = []
    
    # 3. Fetch user's contribution stats
    stats_res = session.execute(
        select(UserContribution.action_type, func.count(UserContribution.id))
        .where(UserContribution.user_id == user_id)
        .group_by(UserContribution.action_type)
    )
    stats_map = {row[0]: row[1] for row in stats_res.fetchall()}
    
    for bdef in all_defs:
        if bdef.id in user_existing_badge_ids:
            continue
            
        awarded = False
        if bdef.condition_type == "first_contribution":
            total = sum(stats_map.values())
            if total >= bdef.condition_threshold:
                awarded = True
        elif bdef.condition_type == "correction_accepted":
            count = stats_map.get("correction_accepted", 0)
            if count >= bdef.condition_threshold:
                awarded = True
        elif bdef.condition_type == "itinerary_forked":
            count = stats_map.get("itinerary_forked", 0)
            if count >= bdef.condition_threshold:
                awarded = True
                
        if awarded:
            ub = UserBadge(user_id=user_id, badge_id=bdef.id)
            session.add(ub)
            newly_awarded.append(ub)
            logger.info(f"Awarded badge {bdef.code} to user {user_id}")

    return newly_awarded


def calculate_level(total_points: int) -> int:
    if total_points < 100:
        return 1
    elif total_points < 300:
        return 2
    elif total_points < 600:
        return 3
    elif total_points < 1000:
        return 4
    return 5


def get_user_passport(session: Session, user_id: uuid.UUID):
    total_points = session.scalar(
        select(func.coalesce(func.sum(UserContribution.points), 0)).where(
            UserContribution.user_id == user_id
        )
    )

    badges_res = session.execute(
        select(UserBadge, BadgeDef)
        .join(BadgeDef)
        .where(UserBadge.user_id == user_id)
        .order_by(UserBadge.created_at.desc())
    )
    
    badges = []
    for ub, bdef in badges_res.all():
        badges.append({
            "id": ub.id,
            "badge_id": ub.badge_id,
            "created_at": ub.created_at,
            "badge_def": bdef
        })
        
    recent_contribs = session.scalars(
        select(UserContribution)
        .where(UserContribution.user_id == user_id)
        .order_by(UserContribution.created_at.desc())
        .limit(10)
    ).all()

    return {
        "user_id": user_id,
        "total_points": total_points,
        "level": calculate_level(total_points),
        "badges": badges,
        "recent_contributions": recent_contribs
    }
