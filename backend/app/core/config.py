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
    amap_web_service_key: str = ""

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
