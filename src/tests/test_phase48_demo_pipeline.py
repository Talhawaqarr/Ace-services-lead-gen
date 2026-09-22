from __future__ import annotations

from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from src.db import SessionLocal
from src.models.core import (
    Contractor,
    IngestionRun,
    MatchRecord,
    MatchReviewAudit,
    OutreachDraft,
    OutreachDraftAudit,
    OutreachQueueItem,
    Project,
    RawContractor,
    RawProject,
)
from src.pipeline.service import (
    DEMO_HARD_MAX_RECORDS,
    build_demo_filters,
    run_bounded_demo_pipeline,
)
from src.providers.live_samgov import LiveSAMGovProvider, SAMGovRateLimitError
from src.outreach.service import (
    build_outreach_draft,
    queue_approved_outreach,
    set_outreach_draft_status,
)
from src.review.service import set_review_status


def _session():
    db = SessionLocal()
    return db


def _reset_samgov(db) -> None:
    project_ids = [row.id for row in db.query(Project.id).filter(Project.source == "samgov").all()]
    if project_ids:
        match_ids = [row.id for row in db.query(MatchRecord.id).filter(MatchRecord.project_id.in_(project_ids)).all()]
        if match_ids:
            draft_ids = [row.id for row in db.query(OutreachDraft.id).filter(OutreachDraft.match_id.in_(match_ids)).all()]
            if draft_ids:
                db.query(OutreachQueueItem).filter(OutreachQueueItem.draft_id.in_(draft_ids)).delete(synchronize_session=False)
                db.query(OutreachDraftAudit).filter(OutreachDraftAudit.draft_id.in_(draft_ids)).delete(synchronize_session=False)
            db.query(OutreachDraft).filter(OutreachDraft.match_id.in_(match_ids)).delete(synchronize_session=False)
            db.query(MatchReviewAudit).filter(MatchReviewAudit.match_id.in_(match_ids)).delete(synchronize_session=False)
            db.query(MatchRecord).filter(MatchRecord.id.in_(match_ids)).delete(synchronize_session=False)
    db.query(Project).filter(Project.source == "samgov").delete(synchronize_session=False)
    db.query(Contractor).filter(Contractor.source == "samgov").delete(synchronize_session=False)
    db.query(RawContractor).filter(RawContractor.source == "samgov").delete(synchronize_session=False)
    db.query(RawProject).filter(RawProject.source == "samgov").delete(synchronize_session=False)
    db.query(IngestionRun).filter(IngestionRun.source == "samgov").delete(synchronize_session=False)
    db.commit()


class _FakeOpportunityProvider:
    source_name = "samgov"

    def __init__(self, records: list[dict[str, Any]] | None = None, error: Exception | None = None):
        self.records = records or []
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def list_projects(self, filters: dict[str, Any] | None = None, page_token: str | None = None):
        self.calls.append(dict(filters or {}))
        if self.error is not None:
            raise self.error
        return {"projects": self.records, "next_page_token": None}

    def get_project_details(self, source_id: str):
        for row in self.records:
            if row.get("source_id") == source_id:
                return row
        raise KeyError(source_id)

    def health_check(self):
        return {"status": "ok"}


def _construction_record(source_id: str = "DEMO-1") -> dict[str, Any]:
    return {
        "source": "samgov",
        "source_id": source_id,
        "solicitationNumber": source_id,
        "title": "Bounded Demo Fire Station Retrofit",
        "description": "Construction and renovation of a municipal fire station facility.",
        "postedDate": "2026-10-10T00:00:00Z",
        "reponseDeadLine": "2099-11-30T17:00:00Z",
        "active": True,
        "type": "Solicitation",
        "naicsCode": "236220",
        "classificationCode": "M",
        "placeOfPerformance": {"city": "Oakland", "state": "CA"},
        "uiLink": "https://sam.gov/opp/demo",
    }


def test_demo_filters_clamp_to_server_hard_max_and_allowlist_query():
    filters, cap = build_demo_filters(
        {"state": "CA", "keyword": "fire", "unexpected": "drop-me"},
        max_records=10_000,
    )
    assert cap == DEMO_HARD_MAX_RECORDS
    assert filters["limit"] == DEMO_HARD_MAX_RECORDS
    assert filters["state"] == "CA"
    assert filters["keyword"] == "fire"
    assert "unexpected" not in filters

    small_filters, small_cap = build_demo_filters(None, max_records=2)
    assert small_cap == 2
    assert small_filters["limit"] == 2

    bad_filters, bad_cap = build_demo_filters(None, max_records="not-a-number")
    assert bad_cap >= 1
    assert bad_filters["limit"] == bad_cap


def test_demo_filters_never_allow_client_to_exceed_hard_max():
    _, cap = build_demo_filters({"state": "CA"}, max_records=DEMO_HARD_MAX_RECORDS * 100)
    assert cap == DEMO_HARD_MAX_RECORDS


def test_demo_run_forwards_bounded_filters_and_scopes_to_run_records():
    db = _session()
    try:
        _reset_samgov(db)
        provider = _FakeOpportunityProvider([_construction_record("DEMO-1")])
        result = run_bounded_demo_pipeline(
            db,
            mode="fixture",
            max_records=50,
            opportunity_provider=provider,
        )
        db.commit()

        assert provider.calls, "provider must be called exactly once per run"
        assert provider.calls[0]["limit"] == DEMO_HARD_MAX_RECORDS
        assert result["records_requested"] == DEMO_HARD_MAX_RECORDS
        assert result["run_source_ids"] == ["DEMO-1"]
        assert result["projects_discovered"] == 1
        assert result["qualified_projects"] == 1
        assert result["matches_generated"] >= 1
        assert result["projects"][0]["source_id"] == "DEMO-1"
        assert result["projects"][0]["qualified"] is True
    finally:
        _reset_samgov(db)
        db.close()


def test_demo_run_zero_results_is_clean_and_commits_nothing():
    db = _session()
    try:
        _reset_samgov(db)
        provider = _FakeOpportunityProvider([])
        result = run_bounded_demo_pipeline(db, mode="fixture", opportunity_provider=provider)
        db.commit()

        assert result["empty"] is True
        assert result["projects_discovered"] == 0
        assert result["qualified_projects"] == 0
        assert result["matches_generated"] == 0
        assert result["run_source_ids"] == []
        assert db.query(Project).filter(Project.source == "samgov").count() == 0
    finally:
        _reset_samgov(db)
        db.close()


def test_demo_run_propagates_rate_limit_without_committing():
    db = _session()
    try:
        _reset_samgov(db)
        provider = _FakeOpportunityProvider(error=SAMGovRateLimitError("rate limited"))
        with pytest.raises(SAMGovRateLimitError):
            run_bounded_demo_pipeline(db, mode="fixture", opportunity_provider=provider)
        db.rollback()
        assert db.query(Project).filter(Project.source == "samgov").count() == 0
    finally:
        _reset_samgov(db)
        db.close()


def test_demo_run_propagates_upstream_http_error():
    db = _session()
    try:
        _reset_samgov(db)
        request = httpx.Request("GET", "https://api.sam.gov/opportunities/v2/search")
        response = httpx.Response(503, request=request)
        provider = _FakeOpportunityProvider(
            error=httpx.HTTPStatusError("upstream failure", request=request, response=response)
        )
        with pytest.raises(httpx.HTTPStatusError):
            run_bounded_demo_pipeline(db, mode="fixture", opportunity_provider=provider)
        db.rollback()
    finally:
        _reset_samgov(db)
        db.close()


def test_demo_run_requires_explicit_live_mode(monkeypatch):
    class _Settings:
        ingestion_mode = "fixture"
        samgov_api_key = "test-key"
        samgov_page_limit = 100
        samgov_max_pages = 1

    monkeypatch.setattr("src.config.get_settings", lambda: _Settings())

    db = _session()
    try:
        with pytest.raises(ValueError, match="INGESTION_MODE=samgov"):
            run_bounded_demo_pipeline(db, mode="live")
    finally:
        db.rollback()
        db.close()


def test_demo_run_rejects_invalid_mode():
    db = _session()
    try:
        with pytest.raises(ValueError, match="Demo mode must be"):
            run_bounded_demo_pipeline(db, mode="bogus")
    finally:
        db.close()


def test_demo_api_rate_limit_maps_to_429(monkeypatch):
    from src import api

    def _raise(*args, **kwargs):
        raise SAMGovRateLimitError("rate limited")

    monkeypatch.setattr(api, "run_bounded_demo_pipeline", _raise)
    client = TestClient(api.app)
    response = client.post("/pipeline/demo/run", json={"mode": "fixture"})
    assert response.status_code == 429
    assert "rate limit" in response.json()["detail"].lower()


def test_demo_api_upstream_error_maps_to_502(monkeypatch):
    from src import api

    request = httpx.Request("GET", "https://api.sam.gov/opportunities/v2/search")
    response = httpx.Response(503, request=request)

    def _raise(*args, **kwargs):
        raise httpx.HTTPStatusError("upstream failure", request=request, response=response)

    monkeypatch.setattr(api, "run_bounded_demo_pipeline", _raise)
    client = TestClient(api.app)
    api_response = client.post("/pipeline/demo/run", json={"mode": "fixture"})
    assert api_response.status_code == 502


def test_demo_api_rejects_live_without_configuration(monkeypatch):
    from src import api

    class _Settings:
        ingestion_mode = "fixture"
        samgov_api_key = None
        samgov_page_limit = 100
        samgov_max_pages = 1

    monkeypatch.setattr("src.config.get_settings", lambda: _Settings())
    client = TestClient(api.app)
    response = client.post("/pipeline/demo/run", json={"mode": "live"})
    assert response.status_code == 400
    assert "live" in response.json()["detail"].lower()


def test_live_provider_demo_budget_issues_one_bounded_request():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"opportunitiesData": [], "totalRecords": 0, "limit": 5, "offset": 0},
        )

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        provider = LiveSAMGovProvider(
            "test-key",
            http_client=client,
            auto_paginate=False,
            max_pages=1,
        )
        result = provider.list_projects({"naics": "23", "limit": DEMO_HARD_MAX_RECORDS})

    assert len(requests) == 1
    assert requests[0].url.params["limit"] == str(DEMO_HARD_MAX_RECORDS)
    assert requests[0].url.params["ncode"] == "23"
    assert result["projects"] == []


def test_demo_offline_end_to_end_reaches_not_sent_queue():
    db = _session()
    try:
        _reset_samgov(db)
        result = run_bounded_demo_pipeline(db, mode="fixture", max_records=3)
        db.commit()
        assert result["opportunities"]["source"] == "samgov"
        assert result["matches_generated"] >= 1

        project = db.query(Project).filter(Project.source == "samgov", Project.source_id == "SAM-1001").one()

        match = (
            db.query(MatchRecord)
            .join(Contractor, Contractor.id == MatchRecord.contractor_id)
            .filter(
                MatchRecord.project_id == project.id,
                MatchRecord.review_status == "UNREVIEWED",
                Contractor.primary_email.isnot(None),
            )
            .order_by(MatchRecord.ranking.asc())
            .first()
        )
        assert match is not None, "expected an unreviewed match with a contractor email"

        set_review_status(db, str(match.id), "APPROVED", actor="demo", source="demo")
        db.commit()

        draft = build_outreach_draft(db, str(match.id), actor="demo", source="demo")
        db.commit()
        assert draft.status == "DRAFT"

        set_outreach_draft_status(db, str(draft.id), "APPROVED", actor="demo", source="demo")
        db.commit()

        item = queue_approved_outreach(db, str(draft.id), actor="demo", source="demo")
        db.commit()

        assert item.status == "QUEUED"
        assert item.recipient_email == draft.recipient_email
        assert item.provenance["delivery"] == "not-sent"

        # Idempotent: queuing again does not create a duplicate row.
        same = queue_approved_outreach(db, str(draft.id), actor="demo", source="demo")
        db.commit()
        assert same.id == item.id
        assert db.query(OutreachQueueItem).filter(OutreachQueueItem.draft_id == draft.id).count() == 1
    finally:
        _reset_samgov(db)
        db.close()


def test_demo_offline_end_to_end_never_sends_email():
    """Queueing must never touch a real email provider."""
    import src.outreach.service as outreach_service

    # No email sending function should exist in the demo path; assert absence.
    assert not hasattr(outreach_service, "send_email")
    assert not hasattr(outreach_service, "send_outreach")


def test_demo_workspace_has_sync_and_queue_controls():
    from pathlib import Path

    source = Path("src/static/app.js").read_text(encoding="utf-8")
    assert "runDemoSync" in source
    assert "/pipeline/demo/run" in source
    assert "/pipeline/demo/limits" in source
    assert "queueOutreachDraft" in source
    assert "/outreach-drafts/' + draftId + '/queue" in source
    assert "Queue Draft (NOT SENT)" in source
    assert "NOT SENT" in source
    assert "/outreach-queue" in source
    # No send controls are introduced.
    assert "sendOutreach" not in source
    assert "send-email" not in source


def test_demo_template_exposes_not_sent_queue_panel():
    from pathlib import Path

    html = Path("src/templates/index.html").read_text(encoding="utf-8")
    assert "NOT SENT" in html
    assert "runDemoSync" in html
    assert "outreachQueue" in html