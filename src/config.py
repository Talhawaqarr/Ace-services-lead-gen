from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_env: str
    database_url: str
    redis_url: str
    ingestion_mode: str
    email_provider: str
    llm_provider: str
    dry_run: bool
    samgov_api_key: str | None = field(default=None, repr=False)
    api_auth_token: str | None = field(default=None, repr=False)
    max_emails_per_hour: int = 100

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    def validate(self) -> None:
        if self.app_env not in {"development", "test", "staging", "production"}:
            raise ValueError("APP_ENV must be development, test, staging, or production")
        if self.ingestion_mode not in {"fixture", "samgov"}:
            raise ValueError("INGESTION_MODE must be fixture or samgov")
        if self.ingestion_mode == "samgov" and not self.samgov_api_key:
            raise ValueError("SAMGOV_API_KEY must be configured when INGESTION_MODE=samgov")
        if self.max_emails_per_hour < 0:
            raise ValueError("MAX_EMAILS_PER_HOUR must be >= 0")
        if self.is_production and self.dry_run:
            raise ValueError("DRY_RUN=true is not allowed when APP_ENV=production")
        if self.is_production and self.email_provider == "mock":
            raise ValueError("EMAIL_PROVIDER=mock is not allowed when APP_ENV=production")
        if self.is_production and not self.api_auth_token:
            raise ValueError("API_AUTH_TOKEN must be configured when APP_ENV=production")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings(
        app_env=os.getenv("APP_ENV", "development").strip().lower(),
        database_url=os.getenv("DATABASE_URL", "postgresql://localhost/ace_dev"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        ingestion_mode=os.getenv("INGESTION_MODE", "fixture").strip().lower(),
        email_provider=os.getenv("EMAIL_PROVIDER", "mock").strip().lower(),
        llm_provider=os.getenv("LLM_PROVIDER", "mock").strip().lower(),
        dry_run=_env_bool("DRY_RUN", True),
        samgov_api_key=os.getenv("SAMGOV_API_KEY") or None,
        api_auth_token=os.getenv("API_AUTH_TOKEN") or None,
        max_emails_per_hour=int(os.getenv("MAX_EMAILS_PER_HOUR", "100")),
    )
    settings.validate()
    return settings


__all__ = ["Settings", "get_settings"]
