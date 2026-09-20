from fastapi.testclient import TestClient

from src.api import app


def test_phase13_readiness_reports_database_ready():
    response = TestClient(app).get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}


def test_phase13_contractors_endpoint_supports_bounded_pagination():
    response = TestClient(app).get("/contractors?limit=2&offset=0")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) <= 2


def test_phase13_projects_endpoint_supports_bounded_pagination():
    response = TestClient(app).get("/projects?limit=2&offset=0")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) <= 2


def test_phase13_pagination_rejects_invalid_limits():
    response = TestClient(app).get("/projects?limit=101")
    assert response.status_code == 422
