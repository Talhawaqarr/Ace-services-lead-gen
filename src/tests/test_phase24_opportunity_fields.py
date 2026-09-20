from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from src.api import app
from src.db import SessionLocal
from src.ingestion.service import ingest_source_records
from src.models.core import Project


class _Provider:
    source_name = "phase24"

    def list_projects(self, _filters):
        return {
            "projects": [
                {
                    "source": "phase24",
                    "source_id": f"OPP-{uuid.uuid4()}",
                    "title": "Operational Fields Test Project",
                    "city": "Faisalabad",
                    "state": "PK",
                    "postedDate": "2026-09-20T10:00:00Z",
                    "reponseDeadLine": "2026-10-20T17:00:00Z",
                    "active": True,
                    "description": "Test opportunity description.",
                    "uiLink": "https://example.test/opportunity",
                }
            ]
        }


def test_ingestion_promotes_operational_opportunity_fields():
    session = SessionLocal()
    try:
        summary = ingest_source_records(session, _Provider(), source_name="phase24")
        assert summary["created"] == 1

        project = session.query(Project).filter(Project.source == "phase24").one()
        assert project.posted_date == "2026-09-20T10:00:00Z"
        assert project.response_deadline == "2026-10-20T17:00:00Z"
        assert project.status == "ACTIVE"
        assert project.description == "Test opportunity description."
        assert project.source_url == "https://example.test/opportunity"
    finally:
        session.rollback()
        session.close()


def test_project_api_exposes_operational_opportunity_fields():
    client = TestClient(app)
    session = SessionLocal()
    try:
        project = Project(
            name="Phase 24 API Project",
            source="phase24-api",
            source_id=str(uuid.uuid4()),
            city="Faisalabad",
            state="PK",
            bid_date="2026-09-20T10:00:00Z",
            posted_date="2026-09-20T10:00:00Z",
            response_deadline="2026-10-20T17:00:00Z",
            status="ACTIVE",
            description="API field test.",
            source_url="https://example.test/api-project",
        )
        session.add(project)
        session.commit()
        project_id = str(project.id)

        response = client.get(f"/projects/{project_id}")
        assert response.status_code == 200
        body = response.json()
        assert body["posted_date"] == "2026-09-20T10:00:00Z"
        assert body["response_deadline"] == "2026-10-20T17:00:00Z"
        assert body["status"] == "ACTIVE"
        assert body["description"] == "API field test."
        assert body["source_url"] == "https://example.test/api-project"
    finally:
        session.query(Project).filter(Project.source == "phase24-api").delete()
        session.commit()
        session.close()
