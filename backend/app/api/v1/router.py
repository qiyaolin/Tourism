from fastapi import APIRouter

from app.api.v1.ai_engine import router as ai_engine_router
from app.api.v1.auth import router as auth_router
from app.api.v1.explore import router as explore_router
from app.api.v1.health import router as health_router
from app.api.v1.itineraries import router as itineraries_router
from app.api.v1.pois import router as pois_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(explore_router)
api_router.include_router(pois_router)
api_router.include_router(itineraries_router)
api_router.include_router(ai_engine_router)
