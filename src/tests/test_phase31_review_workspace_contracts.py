from pathlib import Path


def test_review_workspace_contains_pagination_controls():
    html = Path("src/static/app.js").read_text(encoding="utf-8")
    assert "matchLimit: 10" in html
    assert "matchOffset: 0" in html
    assert "matchStatus: ''" in html
    assert "changeMatchStatus(this.value)" in html
    assert "previousMatchPage()" in html
    assert "nextMatchPage()" in html
    assert "review_status" in html
    assert "limit: String(state.matchLimit)" in html


def test_review_workspace_resets_pagination_when_project_changes():
    html = Path("src/static/app.js").read_text(encoding="utf-8")
    assert "state.matchOffset = 0;" in html
    assert "state.matchStatus = '';" in html
