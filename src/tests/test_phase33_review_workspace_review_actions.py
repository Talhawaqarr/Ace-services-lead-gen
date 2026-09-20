from pathlib import Path


def test_review_action_shows_success_after_refresh():
    html = Path("src/static/app.js").read_text(encoding="utf-8")
    marker = "await refreshProjectMatches();"
    success = "state.message = { type: 'success', text: `Match marked ${status}.` };"
    assert html.index(marker) < html.index(success)
    assert "renderWorkspace();" in html[html.index(success):]


def test_review_action_surfaces_api_error_detail():
    html = Path("src/static/app.js").read_text(encoding="utf-8")
    assert "body.detail || 'Review action failed'" in html
