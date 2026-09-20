from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.outreach.service import queue_approved_outreach


DRAFT_ID = "11111111-1111-1111-1111-111111111111"


def make_session(draft, existing=None):
    session = Mock()
    session.get.return_value = draft
    session.execute.return_value.scalar_one_or_none.return_value = existing
    session.flush.return_value = None
    session.add.return_value = None
    return session


def make_draft(status="APPROVED"):
    return SimpleNamespace(
        id=DRAFT_ID,
        status=status,
        recipient_email="contractor@example.com",
        subject="Estimating support",
        body="Draft body",
        template_version="deterministic-v1",
    )


def test_approved_draft_is_queued_without_sending():
    draft = make_draft()
    session = make_session(draft)

    item = queue_approved_outreach(
        session,
        DRAFT_ID,
        actor="reviewer-1",
        source="workspace",
    )

    assert item.status == "QUEUED"
    assert item.recipient_email == draft.recipient_email
    assert item.subject == draft.subject
    assert item.body == draft.body
    assert item.provenance["delivery"] == "not-sent"
    session.add.assert_called_once()
    session.flush.assert_called_once()


def test_unapproved_draft_cannot_be_queued():
    draft = make_draft(status="DRAFT")
    session = make_session(draft)

    with pytest.raises(ValueError, match="must be APPROVED"):
        queue_approved_outreach(session, DRAFT_ID)

    session.add.assert_not_called()
    session.flush.assert_not_called()


def test_queue_is_idempotent_for_same_draft():
    draft = make_draft()
    existing = SimpleNamespace(id="44444444-4444-4444-4444-444444444444", status="QUEUED")
    session = make_session(draft, existing=existing)

    item = queue_approved_outreach(session, DRAFT_ID)

    assert item is existing
    session.add.assert_not_called()
    session.flush.assert_not_called()
