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
    itinerary_share_base_url: str = "http://localhost:5173/itineraries"
    share_og_base_url: str = "http://localhost:8000/share/itineraries"
    share_default_cover_url: str = ""
    collab_grant_secret: str = ""
    collab_grant_expires_minutes: int = 120
    collab_redis_url: str = "redis://localhost:6379/2"
    collab_flush_interval_seconds: int = 5
    territory_grid_size_deg: float = 0.15
    territory_min_pois: int = 3
    territory_region_name_prefix: str = "守护区域"
    guardian_dormant_window_days: int = 90
    role_regular_min_contributions: int = 3
    role_expert_min_contributions: int = 10
    role_expert_min_age_days: int = 30
    role_guide_min_thanks: int = 20
    role_ambassador_min_areas: int = 3
    bounty_stale_days: int = 45
    bounty_gps_radius_meters: int = 500
    bounty_default_reward_points: int = 20
    bounty_high_freq_daily_limit: int = 5
    bounty_nearby_radius_meters: int = 1500
    bounty_new_user_cooldown_enabled: bool = False
    bounty_new_user_cooldown_days: int = 7
    bounty_new_user_daily_limit: int = 1

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
