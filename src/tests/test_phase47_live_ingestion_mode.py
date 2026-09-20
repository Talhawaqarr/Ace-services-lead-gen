from __future__ import annotations

import os

import pytest

from src.config import Settings


def test_samgov_ingestion_mode_requires_api_key():
    settings = Settings(
        app_env="development",
        database_url="postgresql://localhost/ace_dev",
        redis_url="redis://localhost:6379/0",
        ingestion_mode="samgov",
        email_provider="mock",
        llm_provider="mock",
        dry_run=True,
        samgov_api_key=None,
    )
    with pytest.raises(ValueError, match="SAMGOV_API_KEY"):
        settings.validate()


def test_fixture_mode_does_not_require_samgov_api_key():
    settings = Settings(
        app_env="development",
        database_url="postgresql://localhost/ace_dev",
        redis_url="redis://localhost:6379/0",
        ingestion_mode="fixture",
        email_provider="mock",
        llm_provider="mock",
        dry_run=True,
        samgov_api_key=None,
    )
    settings.validate()
