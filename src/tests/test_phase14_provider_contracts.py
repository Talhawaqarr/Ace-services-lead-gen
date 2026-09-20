from src.providers.contracts import ContractorProvider, OpportunityProvider
from src.providers.samgov import SAMGovProvider
from src.providers.samgov_contractors import SAMGovContractorProvider


def test_samgov_opportunity_provider_implements_contract():
    provider = SAMGovProvider()
    assert isinstance(provider, OpportunityProvider)
    result = provider.list_projects()
    assert set(result) >= {"projects", "next_page_token", "meta"}
    assert provider.health_check()["status"] == "ok"


def test_samgov_contractor_provider_implements_contract():
    provider = SAMGovContractorProvider()
    assert isinstance(provider, ContractorProvider)
    result = provider.list_contractors()
    assert set(result) >= {"contractors", "next_page_token", "meta"}
    assert provider.health_check()["status"] == "ok"


def test_provider_contracts_expose_pagination_and_detail_operations():
    opportunity = SAMGovProvider()
    contractor = SAMGovContractorProvider()
    assert opportunity.list_projects(page_token=None)["next_page_token"] is None
    assert contractor.list_contractors(page_token=None)["next_page_token"] is None
