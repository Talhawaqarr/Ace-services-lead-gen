from __future__ import annotations

import httpx
import pytest

from src.config import Settings
from src.providers.live_samgov_contractors import (
    ENTITY_INFORMATION_V3_URL,
    LiveSAMEntityProvider,
)
from src.providers.samgov_contractors import SAMGovContractorProvider

from src.providers.live_samgov_contractors import (
    ENTITY_INFORMATION_V3_URL,
    LiveSAMEntityProvider,
)


def _entity(
    *,
    uei="R1KJZ8MQP3",
    name="NORTH VALLEY BUILDERS LLC",
    city="SACRAMENTO",
    state="CA",
    naics=(("236220", True), ("541330", False)),
):
    return {
        "entityRegistration": {
            "ueiSAM": uei,
            "legalBusinessName": name,
            "ueiSAMStatus": "ACTIVE",
        },
        "coreData": {
            "registrationStatus": "ACTIVE",
            "entityType": "Business",
            "businessTypes": ["C"],
            "naicsList": [
                {"naicsCode": code, "naicsName": f"NAICS {code}", "isPrimary": primary}
                for code, primary in naics
            ],
            "physicalAddress": {
                "city": city,
                "stateOrProvinceCode": state,
                "zipCode": "95814",
                "countryCode": "USA",
            },
        },
    }


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_provider_targets_v3_endpoint_with_api_key_and_bounded_params():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["params"] = dict(request.url.params)
        return httpx.Response(200, json={"entityData": [_entity()]})

    provider = LiveSAMEntityProvider("secret", http_client=_client(handler), auto_paginate=False)
    provider.list_contractors()

    assert captured["url"].startswith(ENTITY_INFORMATION_V3_URL)
    assert captured["params"]["api_key"] == "secret"
    assert captured["params"]["includeSections"] == "entityRegistration,coreData"
    assert captured["params"]["page"] == "0"
    assert captured["params"]["size"] == "10"


def test_provider_parses_entity_data_and_maps_company_uei_city_state():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"entityData": [_entity()]})

    provider = LiveSAMEntityProvider("secret", http_client=_client(handler), auto_paginate=False)
    result = provider.list_contractors()

    assert len(result["contractors"]) == 1
    contractor = result["contractors"][0]
    assert contractor["source"] == "sam_entity"
    assert contractor["source_id"] == "R1KJZ8MQP3"
    assert contractor["company_name"] == "NORTH VALLEY BUILDERS LLC"
    assert contractor["city"] == "SACRAMENTO"
    assert contractor["state"] == "CA"
    assert contractor["trades"] == ["general"]
    assert result["meta"]["live"] is True
    assert result["meta"]["synthetic"] is False


def test_provider_maps_primary_naics_to_trades_and_keeps_provenance():
    def handler(request: httpx.Request) -> httpx.Response:
        entity = _entity(naics=(("541330", False), ("238210", True)))
        return httpx.Response(200, json={"entityData": [entity]})

    provider = LiveSAMEntityProvider("secret", http_client=_client(handler), auto_paginate=False)
    contractor = provider.list_contractors()["contractors"][0]

    assert contractor["trades"] == ["concrete"]
    assert contractor["provenance"]["naics_codes"] == ["541330", "238210"]
    assert contractor["provenance"]["entity_registration_status"] == "ACTIVE"


def test_provider_tolerates_missing_and_null_nested_fields():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "entityData": [
                    {
                        "entityRegistration": {"ueiSAM": "A1B2C3D4E5", "legalBusinessName": "MINIMAL LLC"},
                        "coreData": None,
                    },
                    {
                        "entityRegistration": {"legalBusinessName": "NO UEI LLC"},
                    },
                    {
                        "entityRegistration": {
                            "ueiSAM": "F6G7H8J9K0",
                            "legalBusinessName": "NULL FIELDS LLC",
                        },
                        "coreData": {
                            "physicalAddress": {"city": None, "stateOrProvinceCode": None},
                            "naicsList": None,
                            "pointsOfContact": None,
                        },
                    },
                ]
            },
        )

    provider = LiveSAMEntityProvider("secret", http_client=_client(handler), auto_paginate=False)
    contractors = provider.list_contractors()["contractors"]

    # The record without a UEI cannot be deduplicated and is dropped.
    assert [row["source_id"] for row in contractors] == ["A1B2C3D4E5", "F6G7H8J9K0"]
    assert contractors[0]["city"] is None
    assert contractors[0]["state"] is None
    assert contractors[0]["trades"] is None
    assert contractors[0]["primary_email"] is None
    assert contractors[0]["website"] is None
    assert contractors[1]["trades"] is None


def test_provider_uses_public_poc_email_when_present_and_never_invents_one():
    def handler(request: httpx.Request) -> httpx.Response:
        entity = _entity()
        entity["coreData"]["pointsOfContact"] = [
            {"firstName": "Dana", "lastName": "Ruiz", "email": "Dana.Ruiz@Example.com"}
        ]
        return httpx.Response(200, json={"entityData": [entity]})

    provider = LiveSAMEntityProvider("secret", http_client=_client(handler), auto_paginate=False)
    contractor = provider.list_contractors()["contractors"][0]

    assert contractor["primary_email"] == "dana.ruiz@example.com"


def test_provider_returns_empty_list_for_empty_entity_data():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"entityData": []})

    provider = LiveSAMEntityProvider("secret", http_client=_client(handler), auto_paginate=False)
    result = provider.list_contractors()

    assert result["contractors"] == []
    assert result["next_page_token"] is None


def test_provider_raises_on_http_error_instead_of_returning_zero():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"message": "Invalid API key"})

    provider = LiveSAMEntityProvider("secret", http_client=_client(handler), auto_paginate=False)
    with pytest.raises(httpx.HTTPStatusError):
        provider.list_contractors()




class _RecordingSession:
    def flush(self):
        return None

    def execute(self, *args, **kwargs):
        raise AssertionError("an empty opportunity fetch must not reach discovery")


def _settings(api_key="secret"):
    return Settings(
        app_env="development",
        database_url="postgresql://localhost/ace_dev",
        redis_url="redis://localhost:6379/0",
        ingestion_mode="samgov",
        email_provider="mock",
        llm_provider="mock",
        dry_run=True,
        samgov_api_key=api_key,
    )


def test_bounded_live_demo_uses_live_sam_entity_contractor_provider(monkeypatch):
    import src.config
    import src.pipeline.service as pipeline

    built = {}

    class _StubEntityProvider:
        def __init__(self, api_key, **kwargs):
            built["api_key"] = api_key
            built["kwargs"] = kwargs
            self.source_name = "sam_entity"

    import src.providers.live_samgov_contractors as entity_module

    monkeypatch.setattr(entity_module, "LiveSAMEntityProvider", _StubEntityProvider)
    monkeypatch.setattr(src.config, "get_settings", lambda: _settings())

    ingested = {}

    def _fake_ingest_contractors(session, provider, source_name=None, **kwargs):
        ingested["source_name"] = source_name
        ingested["provider"] = provider
        return {"source": source_name, "records_fetched": 0, "source_ids": []}

    monkeypatch.setattr(pipeline, "ingest_contractors", _fake_ingest_contractors)
    monkeypatch.setattr(
        pipeline,
        "ingest_source_records",
        lambda *a, **k: {"source": "samgov", "records_fetched": 0, "source_ids": []},
    )

    result = pipeline.run_bounded_demo_pipeline(
        _RecordingSession(),
        mode="live",
        opportunity_provider=object(),
    )

    assert isinstance(built.get("api_key"), str) and built["api_key"] == "secret"
    # Bounded: single page, no auto-pagination.
    assert built["kwargs"]["auto_paginate"] is False
    assert built["kwargs"]["max_pages"] == 1
    # Contractor rows land under the sam_entity source identity.
    assert ingested["source_name"] == "sam_entity"
    assert isinstance(ingested["provider"], _StubEntityProvider)
    assert result["contractors"]["source"] == "sam_entity"


def test_bounded_fixture_demo_still_uses_the_fixture_contractor_provider(monkeypatch):
    import src.config
    import src.pipeline.service as pipeline

    ingested = {}

    def _fake_ingest_contractors(session, provider, source_name=None, **kwargs):
        ingested["source_name"] = source_name
        ingested["provider"] = provider
        return {"source": source_name, "records_fetched": 0, "source_ids": []}

    monkeypatch.setattr(src.config, "get_settings", lambda: _settings())
    monkeypatch.setattr(pipeline, "ingest_contractors", _fake_ingest_contractors)
    monkeypatch.setattr(
        pipeline,
        "ingest_source_records",
        lambda *a, **k: {"source": "samgov", "records_fetched": 0, "source_ids": []},
    )

    result = pipeline.run_bounded_demo_pipeline(
        _RecordingSession(),
        mode="fixture",
        opportunity_provider=object(),
    )

    # The synthetic provider is untouched and still backs the fixture path.
    assert isinstance(ingested["provider"], SAMGovContractorProvider)
    assert ingested["source_name"] == "samgov"
    assert result["contractors"]["source"] == "samgov"
    assert SAMGovContractorProvider().list_contractors()["meta"]["synthetic"] is True


def test_bounded_live_demo_raises_instead_of_falling_back_to_synthetic_contractors(monkeypatch):
    import src.config
    import src.pipeline.service as pipeline

    monkeypatch.setattr(src.config, "get_settings", lambda: _settings(api_key=None))
    monkeypatch.setattr(
        pipeline,
        "ingest_source_records",
        lambda *a, **k: {"source": "samgov", "records_fetched": 0, "source_ids": []},
    )

    with pytest.raises(ValueError, match="API key"):
        pipeline.run_bounded_demo_pipeline(
            _RecordingSession(),
            mode="live",
            opportunity_provider=object(),
        )

def test_provider_raises_when_envelope_is_missing_entity_data():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"totalRecords": 0})

    provider = LiveSAMEntityProvider("secret", http_client=_client(handler), auto_paginate=False)
    with pytest.raises(ValueError, match="entityData"):
        provider.list_contractors()


def test_provider_pagination_is_bounded_by_max_pages():
    pages = []

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        pages.append(page)
        return httpx.Response(
            200, json={"entityData": [_entity(uei=f"UEI{page}", name=f"CO {page}")] * 10}
        )

    provider = LiveSAMEntityProvider(
        "secret", http_client=_client(handler), max_pages=2, auto_paginate=True
    )
    result = provider.list_contractors()

    assert pages == [0, 1]
    assert result["meta"]["pages_fetched"] == 2
    assert result["meta"]["pagination_truncated"] is True
    assert len(result["contractors"]) == 20
    assert result["next_page_token"] is None


def test_provider_stops_paginating_on_a_short_page():
    pages = []

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        pages.append(page)
        return httpx.Response(
            200, json={"entityData": [_entity(uei=f"UEI{page}", name=f"CO {page}")]}
        )

    provider = LiveSAMEntityProvider(
        "secret", http_client=_client(handler), max_pages=5, auto_paginate=True
    )
    result = provider.list_contractors()

    assert pages == [0]
    assert result["meta"]["pagination_truncated"] is False
    assert len(result["contractors"]) == 1


def test_provider_rejects_a_missing_api_key():
    with pytest.raises(ValueError, match="SAMGOV_API_KEY"):
        LiveSAMEntityProvider("   ")

