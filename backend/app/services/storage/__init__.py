from app.core.config import get_settings
from app.services.storage.base import StorageProvider
from app.services.storage.local import LocalStorageProvider


def get_storage_provider() -> StorageProvider:
    settings = get_settings()
    if settings.storage_provider != "local":
        raise ValueError(f"Unsupported storage provider: {settings.storage_provider}")
    return LocalStorageProvider(
        root_dir=settings.storage_local_root,
        public_base_url=settings.storage_public_base_url,
    )
