import pytest

from src.db import get_session
from src.models.core import (
    Contractor,
    IngestionRun,
    MatchRecord,
    MatchReviewAudit,
    Project,
    RawContractor,
    RawProject,
)
from src.pipeline.service import run_local_fixture_pipeline
from src.review.service import set_review_status


@pytest.fixture
def session():
    db = get_session()
    try:
        yield db
    finally:
        db.close()


def _reset_phase12(session):
    session.query(MatchReviewAudit).delete(synchronize_session=False)
    session.query(MatchRecord).delete(synchronize_session=False)
    session.query(Contractor).filter(Contractor.source == "samgov").delete(synchronize_session=False)
    session.query(RawContractor).filter(RawContractor.source == "samgov").delete(synchronize_session=False)
    session.query(Project).filter(Project.source == "samgov").delete(synchronize_session=False)
    session.query(RawProject).filter(RawProject.source == "samgov").delete(synchronize_session=False)
    session.query(IngestionRun).filter(IngestionRun.source == "samgov").delete(synchronize_session=False)
    session.commit()


def test_phase12_complete_offline_pipeline_reaches_persisted_matches_and_review(session):
    _reset_phase12(session)

    result = run_local_fixture_pipeline(session)
    session.commit()

    assert result["opportunities"]["accepted"] >= 3
    assert result["contractors"]["accepted"] >= 3
    assert result["projects_discovered"] == result["projects_processed"]
    assert result["matches_generated"] > 0

    project = session.query(Project).filter(Project.source == "samgov").first()
    matches = (
        session.query(MatchRecord)
        .filter(MatchRecord.project_id == project.id)
        .order_by(MatchRecord.ranking.asc())
        .all()
    )

    assert matches
    assert matches[0].review_status == "UNREVIEWED"
    assert matches[0].matcher_version
    assert matches[0].components is not None
    assert matches[0].positive_factors is not None
    assert matches[0].unknown_factors is not None

    set_review_status(
        session,
        str(matches[0].id),
        "APPROVED",
        actor="phase12-test",
        source="phase12-test",
    )
    session.commit()

    refreshed = session.get(MatchRecord, matches[0].id)
    assert refreshed.review_status == "APPROVED"
    assert refreshed.reviewed_at is not None

    audit = (
        session.query(MatchReviewAudit)
        .filter(MatchReviewAudit.match_id == matches[0].id)
        .one()
    )
    assert audit.previous_status == "UNREVIEWED"
    assert audit.new_status == "APPROVED"
    assert audit.actor == "phase12-test"


def test_phase12_rerun_is_idempotent_for_projects_contractors_and_matches(session):
    _reset_phase12(session)

    first = run_local_fixture_pipeline(session)
    session.commit()
    first_projects = session.query(Project).filter(Project.source == "samgov").count()
    first_contractors = session.query(Contractor).filter(Contractor.source == "samgov").count()
    first_matches = session.query(MatchRecord).count()

    second = run_local_fixture_pipeline(session)
    session.commit()

    assert second["opportunities"]["duplicates"] >= 1
    assert second["contractors"]["duplicates"] >= 1
    assert session.query(Project).filter(Project.source == "samgov").count() == first_projects
    assert session.query(Contractor).filter(Contractor.source == "samgov").count() == first_contractors
    assert session.query(MatchRecord).count() == first_matches


def test_phase12_discovery_does_not_rank_or_score_candidates(session):
    _reset_phase12(session)

    result = run_local_fixture_pipeline(session)
    session.commit()

    project = session.query(Project).filter(Project.source == "samgov").first()
    from src.pipeline.service import discover_contractors

    candidates = discover_contractors(session, project)
    assert candidates
    assert all("match_score" not in candidate for candidate in candidates)
    assert all("ranking" not in candidate for candidate in candidates)


def test_phase12_pipeline_is_fixture_only_by_default(session):
    _reset_phase12(session)

    result = run_local_fixture_pipeline(session)

    assert result["opportunities"]["source"] == "samgov"
    assert result["contractors"]["source"] == "samgov"


def test_phase12_api_exposes_local_pipeline_endpoint(session):
    _reset_phase12(session)

    from fastapi.testclient import TestClient
    from src.api import app

    response = TestClient(app).post("/pipeline/local/run")
    assert response.status_code == 200
    payload = response.json()
    assert payload["matches_generated"] > 0
    assert payload["opportunities"]["source"] == "samgov"
    assert payload["contractors"]["source"] == "samgov"
