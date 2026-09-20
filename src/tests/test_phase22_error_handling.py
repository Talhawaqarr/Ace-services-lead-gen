from __future__ import annotations

import asyncio
import json
import logging

from fastapi import Request

from src.observability import JsonFormatter, request_logging_middleware


def _request(path: str = "/phase22-test", request_id: str = "phase22-test-request") -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [(b"x-request-id", request_id.encode())],
        "query_string": b"",
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("testclient", 50000),
        "root_path": "",
        "http_version": "1.1",
    }
    return Request(scope)


def test_internal_errors_return_request_id_and_generic_message():
    request = _request()

    async def call_next(_request):
        raise RuntimeError("secret implementation detail")

    response = asyncio.run(request_logging_middleware(request, call_next))

    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == "phase22-test-request"
    assert json.loads(response.body)["detail"] == "Internal server error"
    assert "secret implementation detail" not in response.body.decode()


def test_internal_error_logging_contains_request_metadata(caplog):
    request = _request(request_id="phase22-log-request")

    async def call_next(_request):
        raise RuntimeError("boom")

    with caplog.at_level(logging.INFO, logger="ace.api"):
        asyncio.run(request_logging_middleware(request, call_next))

    records = [record for record in caplog.records if record.name == "ace.api" and record.message == "request"]
    assert records
    assert records[-1].status_code == 500
    assert records[-1].method == "GET"
    assert records[-1].path == "/phase22-test"

    payload = json.loads(JsonFormatter().format(records[-1]))
    assert payload["request_id"] == "phase22-log-request"
    assert payload["status_code"] == 500
