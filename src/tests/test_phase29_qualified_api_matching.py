from __future__ import annotations

from fastapi.testclient import TestClient

from src.api import app
from src.db import SessionLocal
from src.models.core import Contractor, MatchRecord, MatchReviewAudit, Project


client = TestClient(app)


def _cleanup_source(source: str) -> None:
    session = SessionLocal()
    try:
        project_ids = [row.id for row in session.query(Project.id).filter(Project.source == source).all()]
        if project_ids:
            match_ids = [row.id for row in session.query(MatchRecord.id).filter(MatchRecord.project_id.in_(project_ids)).all()]
            if match_ids:
                session.query(MatchReviewAudit).filter(MatchReviewAudit.match_id.in_(match_ids)).delete(synchronize_session=False)
                session.query(MatchRecord).filter(MatchRecord.id.in_(match_ids)).delete(synchronize_session=False)
        session.query(Project).filter(Project.source == source).delete(synchronize_session=False)
        session.query(Contractor).filter(Contractor.source == source).delete(synchronize_session=False)
        session.commit()
    finally:
        session.close()


def _seed(source: str, qualified: bool) -> str:
    _cleanup_source(source)
    session = SessionLocal()
    try:
        project = Project(
            name=f"Phase 29 {'Qualified' if qualified else 'Unqualified'}",
            source=source,
            source_id=source,
            state="CA",
            trades=["general"],
            status="ACTIVE" if qualified else "INACTIVE",
            response_deadline="2099-12-31T17:00:00Z",
            provenance={"construction_relevance": "likely" if qualified else "unlikely"},
        )
        session.add(project)
        session.flush()
        session.add(
            Contractor(
                company_name="Phase 29 Contractor",
                normalized_name="phase 29 contractor",
                source=source,
                source_id=f"{source}-contractor",
                state="CA",
                trades=["general"],
            )
        )
        session.commit()
        return str(project.id)
    finally:
        session.close()


def test_match_generation_rejects_unqualified_opportunity():
    project_id = _seed("phase29-unqualified", qualified=False)
    try:
        response = client.post(f"/projects/{project_id}/matches/generate")
        assert response.status_code == 409
        assert response.json()["detail"] == "Opportunity does not qualify for matching"
    finally:
        _cleanup_source("phase29-unqualified")


def test_match_generation_uses_filtered_candidates_for_qualified_opportunity():
    project_id = _seed("phase29-qualified", qualified=True)
    session = SessionLocal()
    try:
        session.add(
            Contractor(
                company_name="Wrong State",
                normalized_name="wrong state",
                source="phase29-qualified",
                source_id="wrong-state",
                state="WA",
                trades=["general"],
            )
        )
        session.add(
            Contractor(
                company_name="Wrong Trade",
                normalized_name="wrong trade",
                source="phase29-qualified",
                source_id="wrong-trade",
                state="CA",
                trades=["electrical"],
            )
        )
        session.commit()
    finally:
        session.close()

    try:
        response = client.post(f"/projects/{project_id}/matches/generate")
        assert response.status_code == 200
        assert response.json()["generated"] == 1
    finally:
        _cleanup_source("phase29-qualified")
