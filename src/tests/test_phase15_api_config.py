from fastapi.testclient import TestClient

from src.api import app


def test_runtime_config_does_not_expose_secret():
    response = TestClient(app).get("/health/config")
    assert response.status_code == 200
    payload = response.json()
    assert payload["app_env"] in {"development", "test", "staging", "production"}
    assert payload["ingestion_mode"] == "fixture"
    assert payload["dry_run"] is True
    assert "samgov_api_key" not in payload
    assert "samgov_api_key_configured" in payload
