from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.base import Base
from src.models.core import Contractor
from src.providers.contracts import ContractorEnrichmentProvider
from src.providers.fixture_enrichment import FixtureContractorEnrichmentProvider
from src.enrichment.service import enrich_contractor


def test_fixture_provider_matches_contract(tmp_path):
    fixture = tmp_path / "enrichment.json"
    fixture.write_text('{"contractors":[{"source_id":"ENT-1","primary_email":" SALES@EXAMPLE.COM ","primary_phone":"+1 555 0102","website":"https://example.com"}]}', encoding="utf-8")
    provider = FixtureContractorEnrichmentProvider(str(fixture))
    assert isinstance(provider, ContractorEnrichmentProvider)
    assert provider.enrich_contractor("ENT-1")["primary_email"] == " SALES@EXAMPLE.COM "


def test_enrichment_fills_missing_fields_and_is_idempotent(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    contractor = Contractor(company_name="Example", normalized_name="Example", source="samgov", source_id="ENT-1")
    session.add(contractor)
    session.commit()

    fixture = tmp_path / "enrichment.json"
    fixture.write_text('{"contractors":[{"source_id":"ENT-1","primary_email":"sales@example.com","primary_phone":"+1 555 0102","website":"https://example.com"}]}', encoding="utf-8")
    provider = FixtureContractorEnrichmentProvider(str(fixture))

    result = enrich_contractor(session, contractor.id, provider)
    assert result["updated_fields"] == ["primary_email", "primary_phone", "website"]
    assert contractor.primary_email == "sales@example.com"

    result2 = enrich_contractor(session, contractor.id, provider)
    assert result2["updated_fields"] == []
    assert len(contractor.provenance["enrichment_history"]) == 2


def test_enrichment_replaces_unranked_contact_with_higher_priority_source(tmp_path):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    contractor = Contractor(
        company_name="Example",
        normalized_name="Example",
        source="samgov",
        source_id="ENT-1",
        primary_email="existing@example.com",
    )
    session.add(contractor)
    session.commit()

    fixture = tmp_path / "enrichment.json"
    fixture.write_text(
        '{"contractors":[{"source_id":"ENT-1","primary_email":"new@example.com","primary_phone":"+1 555 0102"}]}',
        encoding="utf-8",
    )
    provider = FixtureContractorEnrichmentProvider(str(fixture))

    result = enrich_contractor(session, contractor.id, provider)

    assert result["updated_fields"] == ["primary_email", "primary_phone"]
    assert contractor.primary_email == "new@example.com"
    assert contractor.primary_phone == "+1 555 0102"
