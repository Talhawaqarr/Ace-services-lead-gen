from pathlib import Path


def test_workspace_has_outreach_approval_controls():
    html = Path("src/static/app.js").read_text(encoding="utf-8")
    assert "updateOutreachDraftStatus" in html
    assert "/outreach-drafts/' + draftId + '/status" in html
    assert "Approve Draft" in html
    assert "Reject Draft" in html


def test_workspace_loads_outreach_draft_audit_history():
    html = Path("src/static/app.js").read_text(encoding="utf-8")
    assert "outreachAudits" in html
    assert "loadOutreachDraftReviews" in html
    assert "/outreach-drafts/' + draftId + '/reviews" in html


def test_workspace_keeps_draft_only_no_send_action():
    html = Path("src/static/app.js").read_text(encoding="utf-8")
    assert "sendOutreach" not in html
    assert "send-email" not in html
