from __future__ import annotations

import logging

from fastapi.testclient import TestClient

from src.api import app
from src.config import get_settings


def _seed_pipeline() -> dict:
    response = TestClient(app).post("/pipeline/local/run")
    assert response.status_code == 200, response.text
    return response.json()


def test_projects_endpoint_returns_persisted_match_count_without_changing_pagination():
    _seed_pipeline()
    response = TestClient(app).get("/projects?limit=100")

    assert response.status_code == 200
    sam_projects = {item["source_id"]: item for item in response.json() if item["source"] == "samgov"}
    assert "SAM-1001" in sam_projects
    assert sam_projects["SAM-1001"]["match_count"] == 8


def test_project_matches_endpoint_returns_joined_contractor_data():
    _seed_pipeline()
    projects = TestClient(app).get("/projects?limit=100")
    assert projects.status_code == 200

    sam_project = next(item for item in projects.json() if item["source_id"] == "SAM-1001")
    response = TestClient(app).get(f"/projects/{sam_project['id']}/matches")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total"] == 8
    assert all(item["contractor_name"] != "Unknown contractor" for item in payload["matches"])


def test_protected_request_still_gets_request_id_when_authentication_fails(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DRY_RUN", "false")
    monkeypatch.setenv("EMAIL_PROVIDER", "smtp")
    monkeypatch.setenv("API_AUTH_TOKEN", "phase20-test-token")
    get_settings.cache_clear()

    response = TestClient(app).get("/health/config")

    assert response.status_code == 401
    assert response.headers.get("X-Request-ID")

    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("EMAIL_PROVIDER", "mock")
    get_settings.cache_clear()


def test_request_logger_remains_configured_after_api_hardening():
    root = logging.getLogger()
    assert root.handlers
