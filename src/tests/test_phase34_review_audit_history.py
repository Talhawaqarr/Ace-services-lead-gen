from pathlib import Path


def test_review_audit_endpoint_is_exposed():
    source = Path("src/api.py").read_text(encoding="utf-8")
    assert '@app.get("/matches/{match_id}/reviews"' in source
    assert "MatchReviewAudit" in source
    assert "previous_status" in source
    assert "new_status" in source


def test_review_action_keeps_review_audit_metadata():
    source = Path("src/api.py").read_text(encoding="utf-8")
    assert '"actor": audit.actor' in source
    assert '"source": audit.source' in source
    assert '"created_at": audit.created_at.isoformat()' in source
