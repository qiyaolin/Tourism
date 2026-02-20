from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.services.storage.base import StorageProvider


class LocalStorageProvider(StorageProvider):
    def __init__(self, root_dir: str, public_base_url: str) -> None:
        self._root = Path(root_dir)
        self._root.mkdir(parents=True, exist_ok=True)
        self._public_base_url = public_base_url.rstrip("/")

    def save_bytes(self, *, content: bytes, extension: str, content_type: str) -> tuple[str, str]:
        del content_type
        safe_ext = extension.lstrip(".").lower() or "bin"
        now = datetime.now(UTC)
        relative_dir = Path(f"{now.year:04d}/{now.month:02d}")
        relative_path = relative_dir / f"{uuid4().hex}.{safe_ext}"
        absolute_path = self._root / relative_path
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        absolute_path.write_bytes(content)
        storage_key = str(relative_path).replace("\\", "/")
        public_url = f"{self._public_base_url}/{storage_key}"
        return storage_key, public_url
