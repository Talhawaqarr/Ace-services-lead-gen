from __future__ import annotations

import json
import logging

from fastapi.testclient import TestClient

from src.api import app
from src.observability import JsonFormatter


def test_health_response_includes_request_id():
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    request_id = response.headers.get("X-Request-ID")
    assert request_id
    assert len(request_id) > 10


def test_client_request_id_is_preserved():
    request_id = "phase17-test-request"
    response = TestClient(app).get("/health", headers={"X-Request-ID": request_id})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id


def test_json_formatter_contains_request_metadata():
    record = logging.LogRecord(
        name="ace.api",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request",
        args=(),
        exc_info=None,
    )
    record.method = "GET"
    record.path = "/health"
    record.status_code = 200
    record.duration_ms = 1.25

    payload = json.loads(JsonFormatter().format(record))

    assert payload["logger"] == "ace.api"
    assert payload["message"] == "request"
    assert payload["method"] == "GET"
    assert payload["path"] == "/health"
    assert payload["status_code"] == 200
    assert payload["duration_ms"] == 1.25
    assert "request_id" in payload
