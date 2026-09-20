from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api import app
from src.config import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_development_does_not_require_auth(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("API_AUTH_TOKEN", raising=False)

    response = TestClient(app).get("/health/config")

    assert response.status_code == 200


def test_production_requires_api_auth_token_configuration(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DRY_RUN", "false")
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.delenv("API_AUTH_TOKEN", raising=False)

    with pytest.raises(ValueError, match="API_AUTH_TOKEN"):
        get_settings()


def test_production_rejects_missing_credentials(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DRY_RUN", "false")
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("API_AUTH_TOKEN", "phase16-test-token")

    response = TestClient(app).get("/health/config")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_production_accepts_valid_bearer_token(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DRY_RUN", "false")
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("API_AUTH_TOKEN", "phase16-test-token")

    response = TestClient(app).get(
        "/health/config",
        headers={"Authorization": "Bearer phase16-test-token"},
    )

    assert response.status_code == 200
    assert response.json()["app_env"] == "production"
    assert "phase16-test-token" not in response.text


def test_health_endpoints_remain_public_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DRY_RUN", "false")
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("API_AUTH_TOKEN", "phase16-test-token")

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
