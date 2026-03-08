from fastapi import APIRouter

from app.api.v1.admin_bounties import router as admin_bounties_router
from app.api.v1.admin_territories import router as admin_territories_router
from app.api.v1.ai_engine import router as ai_engine_router
from app.api.v1.auth import router as auth_router
from app.api.v1.block_templates import router as block_templates_router
from app.api.v1.blocks import router as blocks_router
from app.api.v1.bounties import router as bounties_router
from app.api.v1.collab import router as collab_router
from app.api.v1.explore import router as explore_router
from app.api.v1.health import router as health_router
from app.api.v1.itineraries import router as itineraries_router
from app.api.v1.itinerary_collab import router as itinerary_collab_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.passports import router as passports_router
from app.api.v1.poi_corrections import router as poi_corrections_router
from app.api.v1.pois import router as pois_router
from app.api.v1.territories import router as territories_router
from app.api.v1.weather import router as weather_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(admin_bounties_router)
api_router.include_router(admin_territories_router)
api_router.include_router(blocks_router)
api_router.include_router(block_templates_router)
api_router.include_router(bounties_router)
api_router.include_router(collab_router)
api_router.include_router(explore_router)
api_router.include_router(pois_router)
api_router.include_router(poi_corrections_router)
api_router.include_router(notifications_router)
api_router.include_router(itineraries_router)
api_router.include_router(itinerary_collab_router)
api_router.include_router(weather_router)
api_router.include_router(ai_engine_router)
api_router.include_router(passports_router, prefix="/passports", tags=["passports"])
api_router.include_router(territories_router)
