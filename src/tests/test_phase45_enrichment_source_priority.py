from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.enrichment.service import enrich_contractor
from src.models.base import Base
from src.models.core import Contractor
from src.providers.fixture_enrichment import FixtureContractorEnrichmentProvider


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _provider(tmp_path, priority=10):
    fixture = tmp_path / "enrichment.json"
    fixture.write_text(
        '{"contractors":[{"source_id":"ENT-1","primary_email":"new@example.com","primary_phone":"+1 555 0102","source_priority":%d}]}'
        % priority,
        encoding="utf-8",
    )
    return FixtureContractorEnrichmentProvider(str(fixture))


def test_higher_priority_source_can_replace_lower_priority_contact(tmp_path):
    session = _session()
    contractor = Contractor(
        company_name="Example", normalized_name="Example", source="samgov", source_id="ENT-1",
        primary_email="old@example.com",
        provenance={"contact_sources":{"primary_email":{"source":"old-source","priority":5}}},
    )
    session.add(contractor)
    session.commit()
    enrich_contractor(session, contractor.id, _provider(tmp_path, priority=10))
    assert contractor.primary_email == "new@example.com"
    assert contractor.provenance["contact_sources"]["primary_email"]["priority"] == 10


def test_equal_priority_does_not_replace_existing_contact(tmp_path):
    session = _session()
    contractor = Contractor(
        company_name="Example", normalized_name="Example", source="samgov", source_id="ENT-1",
        primary_email="old@example.com",
        provenance={"contact_sources":{"primary_email":{"source":"old-source","priority":10}}},
    )
    session.add(contractor)
    session.commit()
    enrich_contractor(session, contractor.id, _provider(tmp_path, priority=10))
    assert contractor.primary_email == "old@example.com"
