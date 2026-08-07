from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://") and "+psycopg2" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://allie:allie@localhost:5432/allie"
    app_password: str = "allie"
    app_secret: str = "change-me-in-production"
    web_origin: str = "http://localhost:5173"
    upload_dir: str = "./uploads"
    token_days: int = 30

    resend_api_key: str = ""
    resend_from: str = "Allie Care <onboarding@resend.dev>"
    cron_secret: str = "dev-cron-secret"

    @field_validator("database_url", mode="before")
    @classmethod
    def _db_url(cls, v: str) -> str:
        return normalize_database_url(str(v))


@lru_cache
def get_settings() -> Settings:
    return Settings()
