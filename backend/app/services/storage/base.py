from abc import ABC, abstractmethod


class StorageProvider(ABC):
    @abstractmethod
    def save_bytes(self, *, content: bytes, extension: str, content_type: str) -> tuple[str, str]:
        """Save raw bytes and return (storage_key, public_url)."""
