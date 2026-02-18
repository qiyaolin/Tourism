from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.db.session import check_database_ready

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", status_code=status.HTTP_200_OK)
def live() -> dict[str, str]:
    return {"status": "ok", "service": "atlas-backend"}


@router.get("/ready")
def ready() -> JSONResponse:
    db_ok = check_database_ready()
    payload = {
        "status": "ready" if db_ok else "degraded",
        "checks": {
            "database": "ok" if db_ok else "error",
        },
    }
    if db_ok:
        return JSONResponse(content=payload, status_code=status.HTTP_200_OK)
    return JSONResponse(content=payload, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
