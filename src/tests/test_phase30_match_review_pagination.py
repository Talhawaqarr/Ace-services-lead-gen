from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from src.api import app
from src.db import SessionLocal
from src.models.core import Contractor, MatchRecord, Project

client = TestClient(app)


def _cleanup(source: str) -> None:
    session = SessionLocal()
    try:
        project_ids = [row.id for row in session.query(Project.id).filter(Project.source == source).all()]
        if project_ids:
            session.query(MatchRecord).filter(MatchRecord.project_id.in_(project_ids)).delete(synchronize_session=False)
        session.query(Project).filter(Project.source == source).delete(synchronize_session=False)
        session.query(Contractor).filter(Contractor.source == source).delete(synchronize_session=False)
        session.commit()
    finally:
        session.close()


def _seed() -> tuple[str, str]:
    source = f"phase30-{uuid.uuid4().hex}"
    session = SessionLocal()
    try:
        project = Project(
            name="Phase 30 Review Pagination",
            source=source,
            source_id=source,
            state="CA",
            trades=["general"],
            status="ACTIVE",
            provenance={"construction_relevance": "likely"},
        )
        contractors = [
            Contractor(
                company_name=f"Phase 30 Contractor {i}",
                normalized_name=f"phase 30 contractor {i}",
                source=source,
                source_id=f"contractor-{i}",
                state="CA",
                trades=["general"],
            )
            for i in range(1, 4)
        ]
        session.add(project)
        session.add_all(contractors)
        session.flush()
        for ranking, contractor in enumerate(contractors, start=1):
            session.add(
                MatchRecord(
                    project_id=project.id,
                    contractor_id=contractor.id,
                    match_score=1.0 - ranking * 0.1,
                    raw_score=10.0 - ranking,
                    max_available_score=10.0,
                    feature_completeness=1.0,
                    confidence="HIGH",
                    matcher_version=f"phase30-{ranking}",
                    ranking=ranking,
                    review_status=["UNREVIEWED", "APPROVED", "REJECTED"][ranking - 1],
                    positive_factors=["trade_overlap"],
                    negative_factors=[],
                    unknown_factors=[],
                    components={"trade_overlap": 1.0},
                )
            )
        session.commit()
        return str(project.id), source
    finally:
        session.close()


def test_project_matches_supports_pagination_and_status_filter():
    project_id, source = _seed()
    try:
        response = client.get(f"/projects/{project_id}/matches?limit=2&offset=1")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 3
        assert body["limit"] == 2
        assert body["offset"] == 1
        assert len(body["matches"]) == 2
        assert body["summary"] == {
            "total": 3,
            "unreviewed": 1,
            "approved": 1,
            "rejected": 1,
            "skipped": 0,
        }

        filtered = client.get(f"/projects/{project_id}/matches?review_status=approved")
        assert filtered.status_code == 200
        filtered_body = filtered.json()
        assert filtered_body["total"] == 1
        assert len(filtered_body["matches"]) == 1
        assert filtered_body["matches"][0]["review_status"] == "APPROVED"
        assert filtered_body["summary"]["total"] == 3
    finally:
        _cleanup(source)


def test_project_matches_rejects_invalid_review_status():
    project_id, source = _seed()
    try:
        response = client.get(f"/projects/{project_id}/matches?review_status=maybe")
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid review status"
    finally:
        _cleanup(source)
