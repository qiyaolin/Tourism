import logging

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.passport import BadgeDef

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_badges():
    badges = [
        {
            "code": "explorer_1",
            "name": "初心探路者",
            "description": "首次提供有效纠错或发布行程",
            "condition_type": "first_contribution",
            "condition_threshold": 1,
            "icon_url": None,
        },
        {
            "code": "inspector_5",
            "name": "严格纠察",
            "description": "5次纠错被采纳",
            "condition_type": "correction_accepted",
            "condition_threshold": 5,
            "icon_url": None,
        },
        {
            "code": "guide_3",
            "name": "引路前驱",
            "description": "3次行程被借鉴",
            "condition_type": "itinerary_forked",
            "condition_threshold": 3,
            "icon_url": None,
        }
    ]

    with SessionLocal() as session:
        for b in badges:
            stmt = select(BadgeDef).where(BadgeDef.code == b["code"])
            result = session.execute(stmt)
            existing = result.scalar_one_or_none()
            if not existing:
                badge = BadgeDef(**b)
                session.add(badge)
                logger.info(f"Added badge: {b['code']}")
            else:
                logger.info(f"Badge {b['code']} already exists")
        session.commit()

if __name__ == "__main__":
    seed_badges()
