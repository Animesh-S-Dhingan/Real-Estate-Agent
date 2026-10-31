"""Application settings loaded from environment."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "EstateAI"
    app_version: str = "2.0.0"
    api_prefix: str = "/api/v1"
    debug: bool = True

    # SQLite by default for local MVP; set DATABASE_URL for Postgres.
    database_url: str = f"sqlite:///{ROOT_DIR / 'data' / 'estateai.db'}"

    secret_key: str = "change-me-estateai-dev-secret-key-32chars"
    access_token_expire_minutes: int = 60 * 12
    algorithm: str = "HS256"

    google_api_key: str | None = None
    google_maps_api_key: str | None = None
    news_api_key: str | None = None

    cors_origins: str = "*"

    # Listing freshness window (days)
    listing_freshness_days: int = 30

    # Default seed admin
    seed_admin_email: str = "admin@estateai.example"
    seed_admin_password: str = "Admin@12345"


@lru_cache
def get_settings() -> Settings:
    return Settings()
