from __future__ import annotations

from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from src.api import run_demo


class SessionContext:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc, tb):
        return False


def test_demo_requires_live_ingestion_mode(monkeypatch):
    from src import api

    settings = Mock(
        ingestion_mode="fixture",
        samgov_api_key=None,
    )
    monkeypatch.setattr(api, "get_settings", lambda: settings)

    with pytest.raises(HTTPException) as exc_info:
        run_demo()

    assert exc_info.value.status_code == 409
    assert "INGESTION_MODE=samgov" in str(exc_info.value.detail)


def test_demo_uses_one_record_construction_filter(monkeypatch):
    from src import api

    settings = Mock(
        ingestion_mode="samgov",
        samgov_api_key="secret",
    )
    provider = Mock()
    pipeline_summary = {
        "demo": True,
        "opportunities": {"records_fetched": 1, "accepted": 1, "rejected": 0, "duplicates": 0, "errors": 0},
        "qualified_projects": 1,
        "projects_processed": 1,
        "candidates_considered": 3,
        "matches_generated": 3,
    }
    session = Mock()
    session_context = SessionContext(session)

    monkeypatch.setattr(api, "get_settings", lambda: settings)
    monkeypatch.setattr(api, "LiveSAMGovProvider", lambda *args, **kwargs: provider)
    monkeypatch.setattr(api, "SAMGovContractorProvider", lambda: Mock())
    monkeypatch.setattr(api, "SessionLocal", lambda: session_context)
    monkeypatch.setattr(api, "run_demo_pipeline", Mock(return_value=pipeline_summary))

    result = run_demo(keyword="36C26126Q1279", state="ca")

    assert result == pipeline_summary
    api.run_demo_pipeline.assert_called_once()
    kwargs = api.run_demo_pipeline.call_args.kwargs
    assert kwargs["filters"] == {
        "keyword": "36C26126Q1279",
        "state": "CA",
        "naics": "236220",
        "limit": 1,
    }
    provider_factory = api.LiveSAMGovProvider
    assert provider_factory.call_args.kwargs["max_pages"] == 1
    session.commit.assert_called_once()


def test_demo_maps_sam_rate_limit_to_429(monkeypatch):
    from src import api

    settings = Mock(ingestion_mode="samgov", samgov_api_key="secret")
    session = Mock()

    monkeypatch.setattr(api, "get_settings", lambda: settings)
    monkeypatch.setattr(api, "LiveSAMGovProvider", lambda *args, **kwargs: Mock())
    monkeypatch.setattr(api, "SAMGovContractorProvider", lambda: Mock())
    monkeypatch.setattr(api, "SessionLocal", lambda: SessionContext(session))
    monkeypatch.setattr(
        api,
        "run_demo_pipeline",
        Mock(side_effect=api.SAMGovRateLimitError("quota")),
    )

    with pytest.raises(HTTPException) as exc_info:
        run_demo()

    assert exc_info.value.status_code == 429
    assert "rate limit" in str(exc_info.value.detail).lower()
    session.rollback.assert_called_once()
    session.commit.assert_not_called()
