from pathlib import Path


def test_review_workspace_handles_project_load_failures():
    html = Path("src/static/app.js").read_text(encoding="utf-8")
    assert "Unable to load projects" in html
    assert "state.message = { type: 'error', text: error.message };" in html
    assert "renderWorkspace();" in html


def test_review_workspace_preserves_visible_match_selection():
    html = Path("src/static/app.js").read_text(encoding="utf-8")
    assert "const visibleMatchIds = new Set(state.projectMatches.matches.map(match => match.id));" in html
    assert "if (!visibleMatchIds.has(state.selectedMatchId))" in html
    assert "state.projectMatches.matches[0]?.id || null" in html
