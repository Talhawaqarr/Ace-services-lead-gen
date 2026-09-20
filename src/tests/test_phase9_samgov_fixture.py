import json
from pathlib import Path

from src.db import get_session
from src.ingestion.service import ingest_source_records
from src.models.core import IngestionRun, MatchRecord, MatchReviewAudit, Project, RawProject
from src.providers.samgov import SAMGovProvider


def _reset_source_data(session):
    project_ids = [row[0] for row in session.query(Project.id).filter(Project.source == "samgov").all()]
    match_ids = [row[0] for row in session.query(MatchRecord.id).filter(MatchRecord.project_id.in_(project_ids)).all()] if project_ids else []
    if match_ids:
        session.query(MatchReviewAudit).filter(MatchReviewAudit.match_id.in_(match_ids)).delete(synchronize_session=False)
        session.query(MatchRecord).filter(MatchRecord.id.in_(match_ids)).delete(synchronize_session=False)
    session.query(Project).filter(Project.source == "samgov").delete(synchronize_session=False)
    session.query(RawProject).filter(RawProject.source == "samgov").delete(synchronize_session=False)
    session.query(IngestionRun).filter(IngestionRun.source == "samgov").delete(synchronize_session=False)
    session.commit()


def test_samgov_fixture_file_loads_and_provider_is_deterministic():
    fixture_path = Path("docs/fixtures/phase9_samgov_opportunities.json")
    assert fixture_path.exists()

    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert len(payload) >= 6
    assert all(item.get("source") == "samgov" for item in payload)

    provider = SAMGovProvider()
    records = provider.list_projects({})["projects"]
    assert len(records) == len(payload)
    assert records[0]["source_id"] == "SAM-1001"
    assert records[0]["solicitationNumber"] == "SAM-1001"
    assert provider.health_check()["info"]["source"] == "samgov"


def test_samgov_ingestion_accepts_valid_construction_record_and_keeps_raw_payload():
    session = get_session()
    _reset_source_data(session)
    provider = SAMGovProvider()

    summary = ingest_source_records(session, provider, source_name="samgov")

    assert summary["accepted"] >= 3
    assert summary["rejected"] >= 1
    project = session.query(Project).filter(Project.source == "samgov", Project.source_id == "SAM-1001").one()
    assert project.name == "Modernization of East Bay Fire Station 7"
    assert project.source == "samgov"
    raw = session.query(RawProject).filter(RawProject.source == "samgov", RawProject.source_id == "SAM-1001").one()
    assert raw.raw_payload["reponseDeadLine"] == "2026-11-30T17:00:00Z"
    assert project.provenance["response_deadline"] == "2026-11-30T17:00:00Z"


def test_samgov_response_deadline_is_preserved_in_raw_and_normalized_in_provenance():
    session = get_session()
    _reset_source_data(session)
    provider = SAMGovProvider()

    ingest_source_records(session, provider, source_name="samgov")
    project = session.query(Project).filter(Project.source == "samgov", Project.source_id == "SAM-1001").one()
    raw = session.query(RawProject).filter(RawProject.source == "samgov", RawProject.source_id == "SAM-1001").one()

    assert "reponseDeadLine" in raw.raw_payload
    assert raw.raw_payload["reponseDeadLine"] == "2026-11-30T17:00:00Z"
    assert project.provenance["response_deadline"] == "2026-11-30T17:00:00Z"
    assert "reponseDeadLine" not in project.provenance


def test_samgov_award_amount_is_not_mapped_to_estimated_value():
    session = get_session()
    _reset_source_data(session)
    provider = SAMGovProvider()

    ingest_source_records(session, provider, source_name="samgov")
    project = session.query(Project).filter(Project.source == "samgov", Project.source_id == "SAM-1001").one()

    assert project.estimated_value is None
    assert project.provenance["award_amount"] == 2470000.0
    assert project.provenance["award_amount_source"] == "data.award.amount"


def test_samgov_duplicate_source_identity_is_idempotent():
    session = get_session()
    _reset_source_data(session)
    provider = SAMGovProvider()

    first = ingest_source_records(session, provider, source_name="samgov")
    second = ingest_source_records(session, provider, source_name="samgov")

    assert first["created"] >= 1
    assert second["duplicates"] >= 1
    assert session.query(Project).filter(Project.source == "samgov", Project.source_id == "SAM-1001").count() == 1


def test_samgov_missing_required_identity_is_rejected():
    session = get_session()
    _reset_source_data(session)
    provider = SAMGovProvider()

    invalid = {"source": "samgov", "title": "Missing Identity", "active": True, "type": "Solicitation"}
    provider.records = [invalid]
    summary = ingest_source_records(session, provider, source_name="samgov")

    assert summary["rejected"] == 1
    assert summary["accepted"] == 0
    raw = session.query(RawProject).filter(RawProject.source == "samgov").one()
    assert raw.status == "REJECTED"
    assert "source_id" in raw.error_detail or "source or source_id" in raw.error_detail
