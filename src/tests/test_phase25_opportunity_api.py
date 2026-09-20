from __future__ import annotations

from datetime import datetime, timezone
import uuid

from fastapi.testclient import TestClient

from src.api import app
from src.db import SessionLocal
from src.models.core import Project


def test_opportunity_queue_filters_active_construction_and_deadline():
    client = TestClient(app)
    session = SessionLocal()
    source = f"phase25-{uuid.uuid4()}"
    try:
        session.add_all([
            Project(
                name="Qualified Construction Opportunity",
                source=source,
                source_id="QUALIFIED",
                state="CA",
                status="ACTIVE",
                response_deadline="2099-10-01T17:00:00Z",
                provenance={"construction_relevance": "likely"},
            ),
            Project(
                name="Inactive Construction Opportunity",
                source=source,
                source_id="INACTIVE",
                state="CA",
                status="INACTIVE",
                response_deadline="2099-10-01T17:00:00Z",
                provenance={"construction_relevance": "likely"},
            ),
            Project(
                name="Non Construction Opportunity",
                source=source,
                source_id="NONCONSTRUCTION",
                state="CA",
                status="ACTIVE",
                response_deadline="2099-10-01T17:00:00Z",
                provenance={"construction_relevance": "unlikely"},
            ),
        ])
        session.commit()

        response = client.get(f"/opportunities?source={source}&state=ca")
        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body) == 1
        assert body[0]["source_id"] == "QUALIFIED"
        assert body[0]["construction_relevance"] == "likely"
    finally:
        session.query(Project).filter(Project.source == source).delete(synchronize_session=False)
        session.commit()
        session.close()


def test_opportunity_qualification_can_disable_default_filters():
    session = SessionLocal()
    source = f"phase25-{uuid.uuid4()}"
    try:
        project = Project(
            name="Flexible Opportunity",
            source=source,
            source_id="FLEX",
            status="INACTIVE",
            response_deadline=None,
            provenance={"construction_relevance": "unknown"},
        )
        session.add(project)
        session.commit()

        client = TestClient(app)
        response = client.get(
            f"/opportunities?source={source}&active_only=false&construction_only=false"
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert len(body) == 1
        assert body[0]["source_id"] == "FLEX"
    finally:
        session.query(Project).filter(Project.source == source).delete(synchronize_session=False)
        session.commit()
        session.close()
