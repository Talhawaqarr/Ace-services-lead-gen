from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.outreach.service import set_outreach_draft_status


def make_session(draft):
    session = Mock()
    session.get.return_value = draft
    session.flush.return_value = None
    session.add.return_value = None
    return session


def test_approve_draft_records_audit_metadata():
    draft = SimpleNamespace(
        id="draft-1",
        status="DRAFT",
        approved_at=None,
        approved_by=None,
        updated_at=None,
    )
    session = make_session(draft)

    updated = set_outreach_draft_status(
        session,
        "draft-1",
        "APPROVED",
        actor="reviewer-1",
        source="review-workspace",
    )

    assert updated.status == "APPROVED"
    assert updated.approved_by == "reviewer-1"
    assert updated.approved_at is not None
    audit = session.add.call_args.args[0]
    assert audit.previous_status == "DRAFT"
    assert audit.new_status == "APPROVED"
    assert audit.actor == "reviewer-1"
    assert audit.source == "review-workspace"


def test_same_status_is_idempotent_without_audit():
    draft = SimpleNamespace(
        id="draft-1",
        status="APPROVED",
        approved_at="existing",
        approved_by="reviewer-1",
        updated_at=None,
    )
    session = make_session(draft)

    updated = set_outreach_draft_status(session, "draft-1", "APPROVED")

    assert updated is draft
    session.add.assert_not_called()
    session.flush.assert_not_called()


def test_invalid_draft_transition_is_rejected():
    draft = SimpleNamespace(
        id="draft-1",
        status="DRAFT",
        approved_at=None,
        approved_by=None,
        updated_at=None,
    )
    session = make_session(draft)

    with pytest.raises(ValueError, match="Invalid outreach draft transition"):
        set_outreach_draft_status(session, "draft-1", "DRAFT")

    session.add.assert_not_called()
    session.flush.assert_not_called()
