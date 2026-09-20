from __future__ import annotations

import pytest

from src.config import get_settings


def test_default_runtime_is_safe_fixture_dry_run(monkeypatch):
    for key in (
        "APP_ENV", "INGESTION_MODE", "EMAIL_PROVIDER", "LLM_PROVIDER",
        "DRY_RUN", "SAMGOV_API_KEY", "MAX_EMAILS_PER_HOUR",
    ):
        monkeypatch.delenv(key, raising=False)

    get_settings.cache_clear()
    settings = get_settings()

    assert settings.app_env == "development"
    assert settings.ingestion_mode == "fixture"
    assert settings.email_provider == "mock"
    assert settings.llm_provider == "mock"
    assert settings.dry_run is True
    assert settings.samgov_api_key is None


def test_production_rejects_dry_run(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DRY_RUN", "true")
    get_settings.cache_clear()

    with pytest.raises(ValueError, match="DRY_RUN"):
        get_settings()


def test_production_rejects_mock_email(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DRY_RUN", "false")
    monkeypatch.setenv("EMAIL_PROVIDER", "mock")
    get_settings.cache_clear()

    with pytest.raises(ValueError, match="EMAIL_PROVIDER"):
        get_settings()


def test_live_ingestion_mode_is_not_enabled_by_configuration(monkeypatch):
    monkeypatch.setenv("INGESTION_MODE", "live")
    get_settings.cache_clear()

    with pytest.raises(ValueError, match="INGESTION_MODE"):
        get_settings()


def test_secret_is_loaded_but_not_exposed_by_settings_repr(monkeypatch):
    monkeypatch.setenv("SAMGOV_API_KEY", "test-secret")
    get_settings.cache_clear()
    settings = get_settings()

    assert settings.samgov_api_key == "test-secret"
    assert "test-secret" not in repr(settings)
