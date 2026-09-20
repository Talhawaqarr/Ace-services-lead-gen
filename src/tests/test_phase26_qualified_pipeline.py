from __future__ import annotations

from src.db import SessionLocal
from src.pipeline.service import run_qualified_fixture_pipeline


def test_qualified_pipeline_matches_only_qualified_opportunities():
    session = SessionLocal()
    try:
        payload = run_qualified_fixture_pipeline(session)

        assert payload["projects_discovered"] == 4
        assert payload["qualified_projects"] == 3
        assert payload["projects_processed"] == 3
        assert payload["matches_generated"] == 24
    finally:
        session.rollback()
        session.close()
