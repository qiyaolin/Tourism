from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Project Atlas API"
    app_env: str = "dev"
    app_port: int = 8000
    database_url: str = "postgresql+psycopg://atlas:atlas@localhost:5432/atlas"
    cors_allow_origins: str = "http://localhost:5173"
    jwt_secret: str = "replace-with-dev-secret"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 120
    phone_lookup_secret: str = "replace-with-dev-phone-secret"
    ai_provider: str = "deepseek"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com"
    gemini_model: str = "gemini-2.0-flash"
    heweather_api_key: str = ""
    heweather_api_host: str = ""  # 开发者专属 API Host，如 abc1234xyz.def.qweatherapi.com
    heweather_timeout_seconds: int = 8
    amap_web_service_key: str = ""
    storage_provider: str = "local"
    storage_local_root: str = "uploads"
    storage_public_base_url: str = "/uploads"
    collab_token_secret: str = "replace-with-dev-collab-secret"
    collab_share_base_url: str = "http://localhost:5173/collab/join"
    collab_grant_secret: str = ""
    collab_grant_expires_minutes: int = 120
    collab_redis_url: str = "redis://localhost:6379/2"
    collab_flush_interval_seconds: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
