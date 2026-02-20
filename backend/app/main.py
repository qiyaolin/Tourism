from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
if settings.storage_provider == "local":
    Path(settings.storage_local_root).mkdir(parents=True, exist_ok=True)
    app.mount(
        settings.storage_public_base_url,
        StaticFiles(directory=settings.storage_local_root),
        name="uploads",
    )
