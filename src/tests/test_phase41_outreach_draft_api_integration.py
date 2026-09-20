from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from src.api import ReviewRequest, get_outreach_draft_reviews, update_outreach_draft_status


class SessionContext:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc, tb):
        return False


def make_draft():
    return SimpleNamespace(
        id="11111111-1111-1111-1111-111111111111",
        match_id="22222222-2222-2222-2222-222222222222",
        template_version="deterministic-v1",
        recipient_email="contractor@example.com",
        subject="Estimating support for Test Project",
        body="Draft body",
        status="DRAFT",
        generated_at=datetime(2026, 1, 1),
        approved_at=None,
        approved_by=None,
        provenance={"generator": "deterministic-template"},
        updated_at=None,
    )


def test_update_outreach_draft_status_api_returns_updated_draft(monkeypatch):
    from src import api

    draft = make_draft()
    session = Mock()
    session.get.return_value = draft
    session.flush.return_value = None
    session.add.return_value = None
    session.commit.return_value = None
    monkeypatch.setattr(api, "SessionLocal", lambda: SessionContext(session))

    response = update_outreach_draft_status(
        draft.id,
        ReviewRequest(status="APPROVED", actor="reviewer-1", source="workspace"),
    )

    assert response.id == draft.id
    assert response.status == "APPROVED"
    assert response.approved_by == "reviewer-1"
    assert response.recipient_email == "contractor@example.com"
    session.commit.assert_called_once()


def test_update_outreach_draft_status_api_maps_invalid_transition_to_400(monkeypatch):
    from src import api

    draft = make_draft()
    draft.status = "APPROVED"
    session = Mock()
    session.get.return_value = draft
    session.flush.return_value = None
    session.add.return_value = None
    monkeypatch.setattr(api, "SessionLocal", lambda: SessionContext(session))

    with pytest.raises(HTTPException) as exc_info:
        update_outreach_draft_status(
            draft.id,
            ReviewRequest(status="DRAFT"),
        )

    assert exc_info.value.status_code == 400
    assert "Invalid outreach draft transition" in str(exc_info.value.detail)
    session.commit.assert_not_called()


def test_get_outreach_draft_reviews_api_returns_audit_history(monkeypatch):
    from src import api

    draft = make_draft()
    audit = SimpleNamespace(
        id="33333333-3333-3333-3333-333333333333",
        draft_id=draft.id,
        previous_status="DRAFT",
        new_status="APPROVED",
        actor="reviewer-1",
        source="workspace",
        created_at=datetime(2026, 1, 2),
    )
    session = Mock()
    session.get.return_value = draft
    session.execute.return_value.scalars.return_value.all.return_value = [audit]
    monkeypatch.setattr(api, "SessionLocal", lambda: SessionContext(session))

    response = get_outreach_draft_reviews(draft.id)

    assert response == [{
        "id": audit.id,
        "draft_id": draft.id,
        "previous_status": "DRAFT",
        "new_status": "APPROVED",
        "actor": "reviewer-1",
        "source": "workspace",
        "created_at": "2026-01-02T00:00:00",
    }]
