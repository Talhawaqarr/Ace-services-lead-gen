from pathlib import Path


def test_workspace_has_outreach_draft_state_and_actions():
    html = Path("src/templates/index.html").read_text(encoding="utf-8")
    assert "outreachDrafts: {}" in html
    assert "loadOutreachDraft" in html
    assert "generateOutreachDraft" in html
    assert "/outreach-draft" in html


def test_workspace_gates_draft_generation_on_approval():
    html = Path("src/templates/index.html").read_text(encoding="utf-8")
    assert "selectedMatch.review_status !== 'APPROVED'" in html
    assert "Approve this match to generate an outreach draft." in html
    assert "Generate Outreach Draft" in html


def test_workspace_renders_draft_content_without_sending_email():
    html = Path("src/templates/index.html").read_text(encoding="utf-8")
    assert "recipient_email" in html
    assert "subject" in html
    assert "body" in html
    assert "method: 'POST'" in html
