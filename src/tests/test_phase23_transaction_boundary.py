from __future__ import annotations

import uuid

from src.db import SessionLocal
from src.ingestion.service import ingest_source_records
from src.models.core import IngestionRun, Project, RawProject


class _Provider:
    source_name = "phase23"

    def list_projects(self, _filters):
        return {
            "projects": [
                {
                    "source": "phase23",
                    "source_id": f"rollback-{uuid.uuid4()}",
                    "title": "Phase 23 Transaction Boundary Test",
                    "city": "Faisalabad",
                    "state": "PK",
                }
            ]
        }


def test_ingestion_does_not_commit_its_own_transaction():
    session = SessionLocal()
    try:
        summary = ingest_source_records(session, _Provider(), source_name="phase23")
        assert summary["created"] == 1

        session.rollback()

        assert session.query(Project).filter(Project.source == "phase23").count() == 0
        assert session.query(RawProject).filter(RawProject.source == "phase23").count() == 0
        assert session.query(IngestionRun).filter(IngestionRun.source == "phase23").count() == 0
    finally:
        session.close()
