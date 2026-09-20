from __future__ import annotations

from datetime import datetime, timezone

from src.opportunity.service import qualifies_opportunity
from src.models.core import Project


def _project(**overrides):
    values = {"name": "Phase 25 Opportunity", "source": "samgov", "source_id": "P25-1", "status": "ACTIVE", "response_deadline": "2026-10-10T17:00:00Z", "provenance": {"construction_relevance": "likely"}}
    values.update(overrides)
    return Project(**values)


def test_qualifies_active_construction_opportunity():
    project = _project()
    now = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
    assert qualifies_opportunity(project, now=now)


def test_rejects_inactive_opportunity():
    assert not qualifies_opportunity(_project(status="INACTIVE"))


def test_rejects_non_construction_opportunity():
    assert not qualifies_opportunity(_project(provenance={"construction_relevance": "unlikely"}))


def test_deadline_window_is_deterministic():
    project = _project()
    now = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
    assert qualifies_opportunity(project, now=now, deadline_within_days=21)
    assert not qualifies_opportunity(project, now=now, deadline_within_days=10)


def test_missing_deadline_is_rejected_when_window_requested():
    project = _project(response_deadline=None)
    now = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
    assert not qualifies_opportunity(project, now=now, deadline_within_days=30)
