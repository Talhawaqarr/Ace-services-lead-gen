import json
import uuid
from pathlib import Path

from src.db import get_session
from src.ingestion.service import ingest_contractors
from src.matching.engine import match_project
from src.models.core import Contractor, IngestionRun, RawProject
from src.providers.samgov_contractors import SAMGovContractorProvider


def _reset_contractors(session):
    session.query(Contractor).filter(Contractor.source == "samgov").delete(synchronize_session=False)
    session.query(RawProject).filter(RawProject.source == "samgov").delete(synchronize_session=False)
    session.query(IngestionRun).filter(IngestionRun.source == "samgov").delete(synchronize_session=False)
    session.commit()


def test_phase11_fixture_file_loads_and_provider_is_deterministic():
    fixture_path = Path("docs/fixtures/phase11_samgov_contractors.json")
    assert fixture_path.exists()

    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert len(payload) >= 6
    assert all(item.get("source") == "samgov" for item in payload)
    assert all("SYNTHETIC TEST DATA" in json.dumps(item, ensure_ascii=False) for item in payload)

    provider = SAMGovContractorProvider()
    records = provider.list_contractors({})["contractors"]
    assert len(records) == len(payload)
    assert provider.health_check()["info"]["source"] == "samgov"
    assert provider.health_check()["info"]["synthetic"] is True


def test_phase11_valid_contractor_is_accepted_and_uses_stable_source_identity():
    session = get_session()
    _reset_contractors(session)
    provider = SAMGovContractorProvider()

    summary = ingest_contractors(session, provider, source_name="samgov")

    assert summary["accepted"] >= 2
    contractor = session.query(Contractor).filter(Contractor.source == "samgov", Contractor.source_id == "SAMC-1001").one()
    assert contractor.company_name == "North Valley Builders LLC"
    assert contractor.normalized_name == "North Valley Builders LLC"
    assert contractor.state == "CA"
    assert contractor.city == "Sacramento"
    assert contractor.trades == ["general"]
    assert contractor.primary_email == "hello@northvalleybuild.com"


def test_phase11_missing_optional_fields_are_handled_without_failing_record():
    session = get_session()
    _reset_contractors(session)
    provider = SAMGovContractorProvider()

    summary = ingest_contractors(session, provider, source_name="samgov")

    contractor = session.query(Contractor).filter(Contractor.source == "samgov", Contractor.source_id == "SAMC-1003").one()
    assert contractor.company_name == "Westside Renovation Group"
    assert contractor.city is None
    assert contractor.state is None
    assert contractor.primary_email is None
    assert contractor.trades in (None, [])
    assert summary["accepted"] >= 3


def test_phase11_invalid_missing_source_identity_is_rejected():
    session = get_session()
    _reset_contractors(session)
    provider = SAMGovContractorProvider()
    provider.records = [{
        "source": "samgov",
        "company_name": "Missing Identity Builders",
        "trade": "general",
        "contact": {"email": "hello@example.com"},
        "synth": True,
        "notes": "SYNTHETIC TEST DATA",
    }]

    summary = ingest_contractors(session, provider, source_name="samgov")

    assert summary["rejected"] == 1
    raw = session.query(RawProject).filter(RawProject.source == "samgov").one()
    assert raw.status == "REJECTED"
    assert "source_id" in (raw.error_detail or "")


def test_phase11_duplicate_source_identity_is_detected_and_idempotent():
    session = get_session()
    _reset_contractors(session)
    provider = SAMGovContractorProvider()

    first = ingest_contractors(session, provider, source_name="samgov")
    second = ingest_contractors(session, provider, source_name="samgov")

    assert first["accepted"] >= 1
    assert second["duplicates"] >= 1
    assert session.query(Contractor).filter(Contractor.source == "samgov", Contractor.source_id == "SAMC-1001").count() == 1


def test_phase11_same_company_name_different_source_id_remains_distinct():
    session = get_session()
    _reset_contractors(session)
    provider = SAMGovContractorProvider()

    ingest_contractors(session, provider, source_name="samgov")

    records = session.query(Contractor).filter(Contractor.company_name == "Valley Trade Works").all()
    assert len(records) >= 2
    assert {row.source_id for row in records} == {"SAMC-1007", "SAMC-1008"}


def test_phase11_raw_payload_and_provenance_are_preserved():
    session = get_session()
    _reset_contractors(session)
    provider = SAMGovContractorProvider()

    ingest_contractors(session, provider, source_name="samgov")

    raw = session.query(RawProject).filter(RawProject.source == "samgov", RawProject.source_id == "SAMC-1001").one()
    assert raw.raw_payload["source_id"] == "SAMC-1001"
    assert raw.raw_payload["notes"] == "SYNTHETIC TEST DATA"
    contractor = session.query(Contractor).filter(Contractor.source == "samgov", Contractor.source_id == "SAMC-1001").one()
    assert contractor.provenance["source"] == "samgov"
    assert contractor.provenance["source_id"] == "SAMC-1001"
    assert contractor.provenance["fetched_at"]


def test_phase11_normalization_company_state_trade_and_email():
    session = get_session()
    _reset_contractors(session)
    provider = SAMGovContractorProvider()

    ingest_contractors(session, provider, source_name="samgov")

    contractor = session.query(Contractor).filter(Contractor.source == "samgov", Contractor.source_id == "SAMC-1002").one()
    assert contractor.company_name == "Blue Oak Construction Co."
    assert contractor.normalized_name == "Blue Oak Construction Co."
    assert contractor.state == "WA"
    assert contractor.trades == ["electrical", "general"]
    assert contractor.primary_email == "bid@blueoakconstruction.com"


def test_phase11_future_fields_remain_outside_canonical_contractor_model():
    session = get_session()
    _reset_contractors(session)
    provider = SAMGovContractorProvider()

    ingest_contractors(session, provider, source_name="samgov")

    contractor = session.query(Contractor).filter(Contractor.source == "samgov", Contractor.source_id == "SAMC-1001").one()
    assert set(contractor.__table__.columns.keys()) == {
        "id",
        "company_name",
        "normalized_name",
        "source",
        "source_id",
        "city",
        "state",
        "trades",
        "primary_email",
        "provenance",
        "created_at",
        "updated_at",
    }
    assert "website" not in contractor.__dict__
    assert contractor.provenance["raw_payload"]["website"] == "https://northvalleybuild.com"


def test_phase11_non_construction_entity_is_preserved_without_silent_classification():
    session = get_session()
    _reset_contractors(session)
    provider = SAMGovContractorProvider()

    ingest_contractors(session, provider, source_name="samgov")

    contractor = session.query(Contractor).filter(Contractor.source == "samgov", Contractor.source_id == "SAMC-1006").one()
    assert contractor.company_name == "Regional Housing Authority"
    assert contractor.trades in (None, [])
    assert contractor.provenance["construction_relevance"] == "heuristic: likely not construction"


def test_phase11_samgov_contractors_can_participate_in_existing_matcher():
    session = get_session()
    _reset_contractors(session)
    provider = SAMGovContractorProvider()
    ingest_contractors(session, provider, source_name="samgov")

    project = {
        "id": "proj-sam-1",
        "name": "School Modernization",
        "source": "samgov",
        "source_id": "proj-sam-1",
        "city": "Sacramento",
        "state": "CA",
        "latitude": 38.5816,
        "longitude": -121.4944,
        "trades": ["general"],
        "bid_date": "2026-09-15",
        "estimated_value": 1500000,
        "provenance": {"source": "synthetic"},
    }

    contractors = []
    for row in session.query(Contractor).filter(Contractor.source == "samgov").all():
        contractors.append({
            "id": str(row.id),
            "company_name": row.company_name,
            "normalized_name": row.normalized_name,
            "source": row.source,
            "source_id": row.source_id,
            "city": row.city,
            "state": row.state,
            "latitude": None,
            "longitude": None,
            "trades": row.trades,
            "primary_email": row.primary_email,
            "provenance": row.provenance,
        })

    matches = match_project(project, contractors)
    assert any(item["contractor_id"] == str(session.query(Contractor).filter(Contractor.source == "samgov", Contractor.source_id == "SAMC-1001").one().id) for item in matches)


def test_phase11_no_live_network_calls_are_present():
    provider = SAMGovContractorProvider()
    info = provider.health_check()["info"]
    assert info["live_integration_disabled"] is True
    assert info["synthetic"] is True
    assert info["source"] == "samgov"
    assert "http" not in str(info).lower()
