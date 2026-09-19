import uuid

from src.db import get_session
from src.ingestion.service import IngestionSummary, ingest_source_records
from src.models.core import IngestionRun, Project, RawProject


def _reset_source_data(session):
    session.query(Project).filter(Project.source == "usaspending").delete(synchronize_session=False)
    session.query(RawProject).filter(RawProject.source == "usaspending").delete(synchronize_session=False)
    session.query(IngestionRun).filter(IngestionRun.source == "usaspending").delete(synchronize_session=False)
    session.commit()


class _FixtureProvider:
    def __init__(self, records):
        self.records = records

    def list_projects(self, filters=None, page_token=None):
        return {"projects": self.records, "next_page_token": None}


def _project_payload(**overrides):
    row = {
        "source": "usaspending",
        "source_id": "award-1001",
        "title": "New Fire Station Retrofit",
        "description": "Retrofit and modernization of a municipal fire station.",
        "city": "  Sacramento ",
        "state": "CA",
        "bid_date": "2026-12-15",
        "estimated_value": 1500000,
        "trades": ["general"],
        "location": {"city": "Sacramento", "state": "CA"},
    }
    row.update(overrides)
    return row


def test_ingestion_accepts_valid_and_incomplete_projects():
    session = get_session()
    _reset_source_data(session)
    provider = _FixtureProvider([
        _project_payload(),
        _project_payload(source_id="award-1002", title="School HVAC Upgrade", city="Oakland", state="CA", trades=[], bid_date=None),
        _project_payload(source_id="award-1003", title="", city="", state="", trades=[]),
    ])

    summary = ingest_source_records(session, provider, source_name="usaspending")

    assert summary["accepted"] == 2
    assert summary["rejected"] == 1
    assert session.query(Project).filter(Project.source == "usaspending").count() == 2
    assert session.query(Project).filter(Project.source_id == "award-1002").one().bid_date is None


def test_ingestion_is_idempotent_for_same_source_id():
    session = get_session()
    _reset_source_data(session)
    provider = _FixtureProvider([_project_payload(source_id="award-repeat", title="Repeat Project", city=" Fresno ", state="CA")])

    first = ingest_source_records(session, provider, source_name="usaspending")
    second = ingest_source_records(session, provider, source_name="usaspending")

    assert first["created"] == 1
    assert second["duplicates"] == 1
    assert second["updated"] == 0
    assert session.query(Project).filter(Project.source == "usaspending", Project.source_id == "award-repeat").count() == 1


def test_raw_records_store_original_payload_and_error_status():
    session = get_session()
    _reset_source_data(session)
    bad_payload = {"source": "usaspending", "source_id": "bad-1", "title": "", "state": "Z", "city": "NYC", "bid_date": "not-a-date"}
    provider = _FixtureProvider([bad_payload])

    summary = ingest_source_records(session, provider, source_name="usaspending")

    assert summary["rejected"] == 1
    raw = session.query(RawProject).filter(RawProject.source == "usaspending", RawProject.source_id == "bad-1").one()
    assert raw.status == "REJECTED"
    assert raw.raw_payload["title"] == ""
    assert raw.error_detail is not None


def test_ingestion_summary_reports_counts():
    session = get_session()
    _reset_source_data(session)
    provider = _FixtureProvider([
        _project_payload(source_id="count-1", city="Los Angeles", state="CA"),
        _project_payload(source_id="count-2", city="San Diego", state="CA"),
        _project_payload(source_id="count-1", city="Los Angeles", state="CA"),
        {"source": "usaspending", "source_id": "count-bad", "title": "", "state": "CA", "city": "Austin", "bid_date": "bad-date"},
    ])

    summary = ingest_source_records(session, provider, source_name="usaspending")

    assert summary["records_fetched"] == 4
    assert summary["accepted"] == 2
    assert summary["duplicates"] == 1
    assert summary["rejected"] == 1
    assert summary["created"] == 2
