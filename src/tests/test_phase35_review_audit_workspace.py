from pathlib import Path

def test_review_workspace_loads_audit_history():
    source = Path("src/templates/index.html").read_text(encoding="utf-8")
    assert "/matches/${matchId}/reviews" in source
    assert "reviewAudits" in source
    assert "loadMatchReviews" in source
    assert "Review History" in source

def test_review_workspace_displays_audit_metadata():
    source = Path("src/templates/index.html").read_text(encoding="utf-8")
    assert "previous_status" in source
    assert "new_status" in source
    assert "audit.actor" in source
    assert "audit.source" in source
    assert "audit.created_at" in source