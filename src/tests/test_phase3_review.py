import uuid

from src.db import get_session
from src.matching.engine import match_project
from src.models.core import MatchRecord, MatchReviewAudit
from src.review.service import create_match_record, generate_matches, set_review_status


def _project(**overrides):
    data = {
        "id": str(uuid.uuid4()),
        "name": "Phase 3 Review Project",
        "source": "synthetic",
        "source_id": f"proj-{uuid.uuid4()}",
        "city": "Sacramento",
        "state": "CA",
        "latitude": 38.5816,
        "longitude": -121.4944,
        "trades": ["general"],
        "estimated_value": 1000000,
        "bid_date": "2026-12-01",
    }
    data.update(overrides)
    return data


def _contractor(**overrides):
    data = {
        "id": str(uuid.uuid4()),
        "company_name": "Alpha Builders",
        "normalized_name": "Alpha Builders",
        "source": "synthetic",
        "source_id": f"cont-{uuid.uuid4()}",
        "city": "Sacramento",
        "state": "CA",
        "latitude": 38.5816,
        "longitude": -121.4944,
        "trades": ["general"],
    }
    data.update(overrides)
    return data


def test_match_generation_persists_and_is_idempotent():
    session = get_session()
    project = _project()
    contractor = _contractor(id=str(uuid.uuid4()), company_name="Alpha Builders", trades=["general"])
    contractor_b = _contractor(id=str(uuid.uuid4()), company_name="Beta Builders", trades=["electrical"], city="Denver", state="CO")

    baseline_count = session.query(MatchRecord).count()
    first = generate_matches(session, project, [contractor, contractor_b])
    second = generate_matches(session, project, [contractor, contractor_b])

    assert len(first) == 2
    assert len(second) == 2
    assert session.query(MatchRecord).count() == baseline_count + 2


def test_review_status_changes_are_persisted_and_audited():
    session = get_session()
    project = _project()
    contractor = _contractor(id=str(uuid.uuid4()), company_name="Review Builders", trades=["general"])
    results = match_project(project, [contractor])
    record = create_match_record(session, results[0])
    session.add(record)
    session.commit()

    updated = set_review_status(session, str(record.id), "APPROVED")
    assert updated.review_status == "APPROVED"
    assert updated.reviewed_at is not None
    assert session.query(MatchReviewAudit).filter_by(match_id=record.id, new_status="APPROVED").count() == 1


def test_invalid_transition_is_rejected_by_validation():
    session = get_session()
    project = _project()
    contractor = _contractor(id=str(uuid.uuid4()), company_name="Invalid Builders", trades=["general"])
    result = match_project(project, [contractor])[0]
    record = create_match_record(session, result)
    session.add(record)
    session.commit()

    try:
        set_review_status(session, str(record.id), "NOT_A_STATE")
        assert False, "Expected ValueError for invalid review state"
    except ValueError:
        pass


def test_match_record_keeps_exact_phase2_result_snapshot():
    session = get_session()
    project = _project()
    contractor = _contractor(id=str(uuid.uuid4()), company_name="Snapshot Builders", trades=["general"]) 
    result = match_project(project, [contractor])[0]
    record = create_match_record(session, result)
    session.add(record)
    session.commit()

    persisted = session.get(MatchRecord, record.id)
    assert persisted.match_score == result["match_score"]
    assert persisted.confidence == result["confidence"]
    assert persisted.components == result["components"]
    assert persisted.positive_factors == result["positive_factors"]


# This is intentionally a local-safe Phase 3 verification; no external calls are made.
