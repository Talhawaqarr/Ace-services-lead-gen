from __future__ import annotations

from src.db import SessionLocal
from src.pipeline.service import run_qualified_fixture_pipeline


def test_qualified_pipeline_matches_only_qualified_opportunities():
    session = SessionLocal()
    try:
        payload = run_qualified_fixture_pipeline(session)

        # Three fixture notices are discovered; only the two 23xxx construction
        # ones qualify, because qualification now requires a construction NAICS.
        assert payload["projects_discovered"] == 3
        assert payload["qualified_projects"] == 2
        assert payload["projects_processed"] == 2
        assert payload["matches_generated"] == 5
    finally:
        session.rollback()
        session.close()
