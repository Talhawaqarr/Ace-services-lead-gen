from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import pytest

from src.providers.live_samgov import (
    CONSTRUCTION_NAICS_CATEGORY,
    DEFAULT_TARGET_CANDIDATES,
    HARD_MAX_CANDIDATES,
    LiveSAMGovProvider,
    SAMGovRateLimitError,
)
from src.providers.samgov import SAMGovProvider


def test_live_provider_maps_sam_response_and_paginates():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["api_key"] == "secret"
        assert request.url.params["postedFrom"] == "08/01/2026"
        assert request.url.params["postedTo"] == "08/31/2026"
        assert request.url.params["limit"] == "2"
        return httpx.Response(
            200,
            json={
                "totalRecords": 5,
                "limit": 2,
                "offset": 0,
                "opportunitiesData": [
                    {"noticeId": "N-1", "solicitationNumber": "S-1", "title": "Build", "uiLink": "https://sam.gov/opp/N-1"}
                ],
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = LiveSAMGovProvider("secret", http_client=client, auto_paginate=False)

    result = provider.list_projects(
        {"posted_from": "08/01/2026", "posted_to": "08/31/2026", "limit": 2}
    )

    assert result["projects"][0]["source"] == "samgov"
    assert result["projects"][0]["noticeId"] == "N-1"
    assert result["next_page_token"] == "2"
    assert result["meta"]["live"] is True


def test_live_provider_auto_paginates_all_pages():
    offsets = []

    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params["offset"])
        offsets.append(offset)
        records = [
            {"noticeId": f"N-{offset + 1}", "solicitationNumber": f"S-{offset + 1}", "title": "Build"}
        ]
        return httpx.Response(
            200,
            json={
                "totalRecords": 3,
                "limit": 1,
                "offset": offset,
                "opportunitiesData": records,
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = LiveSAMGovProvider("secret", http_client=client, max_pages=5)

    result = provider.list_projects({"limit": 1})

    assert offsets == [0, 1, 2]
    assert len(result["projects"]) == 3
    assert result["next_page_token"] is None
    assert result["meta"]["pages_fetched"] == 3
    assert result["meta"]["records_returned"] == 3


def test_live_provider_retries_rate_limit():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(
            200,
            json={
                "totalRecords": 1,
                "limit": 1,
                "offset": 0,
                "opportunitiesData": [
                    {"noticeId": "N-1", "solicitationNumber": "S-1", "title": "Build"}
                ],
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = LiveSAMGovProvider(
        "secret",
        http_client=client,
        retry_backoff_seconds=0,
        max_retries=1,
    )

    result = provider.list_projects({"limit": 1})

    assert attempts == 2
    assert len(result["projects"]) == 1


def test_live_provider_rejects_missing_api_key():
    try:
        LiveSAMGovProvider("")
    except ValueError as exc:
        assert "SAMGOV_API_KEY" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_live_provider_stops_at_max_pages_without_failing():
    offsets = []

    def handler(request: httpx.Request) -> httpx.Response:
        offset = int(request.url.params["offset"])
        offsets.append(offset)
        return httpx.Response(
            200,
            json={
                "totalRecords": 3,
                "limit": 1,
                "offset": offset,
                "opportunitiesData": [
                    {
                        "noticeId": f"N-{offset + 1}",
                        "solicitationNumber": f"S-{offset + 1}",
                        "title": "Build",
                    }
                ],
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = LiveSAMGovProvider("secret", http_client=client, max_pages=1)

    result = provider.list_projects({"limit": 1})

    assert offsets == [0]
    assert len(result["projects"]) == 1
    assert result["meta"]["pages_fetched"] == 1
    assert result["meta"]["records_returned"] == 1
    assert result["meta"]["pagination_truncated"] is True


# --- Targeted construction search and bounded candidate retrieval ---


def _paged_handler(records_per_page: int, total_records: int, requested: list):
    """Serve a large result set page by page and record each request's params."""

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(dict(request.url.params))
        offset = int(request.url.params["offset"])
        limit = int(request.url.params["limit"])
        rows = [
            {
                "noticeId": f"N-{offset + index + 1}",
                "solicitationNumber": f"S-{offset + index + 1}",
                "title": "Construction of sidewalks",
                "naicsCode": "236220",
                "type": "Solicitation",
            }
            for index in range(min(limit, records_per_page))
        ]
        return httpx.Response(
            200,
            json={
                "totalRecords": total_records,
                "limit": limit,
                "offset": offset,
                "opportunitiesData": rows,
            },
        )

    return handler


def _empty_handler(requested: list):
    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(dict(request.url.params))
        return httpx.Response(
            200,
            json={
                "totalRecords": 0,
                "limit": int(request.url.params["limit"]),
                "offset": 0,
                "opportunitiesData": [],
            },
        )

    return handler


def test_live_provider_requests_construction_and_active_targeted_search():
    requested: list = []
    client = httpx.Client(transport=httpx.MockTransport(_empty_handler(requested)))
    provider = LiveSAMGovProvider("secret", http_client=client)

    result = provider.list_projects({"limit": 20})

    params = requested[0]
    # NAICS construction category through the documented `ncode` filter.
    assert params["ncode"] == CONSTRUCTION_NAICS_CATEGORY == "23"
    # Active opportunities through the documented `status` filter.
    assert params["status"] == "active"
    # The mandatory posted-date window and bounded paging are unchanged.
    assert params["postedFrom"] and params["postedTo"]
    assert params["limit"] == "20"
    assert params["offset"] == "0"
    # API key handling is preserved and never echoed into meta.
    assert params["api_key"] == "secret"
    assert "api_key" not in result["meta"]["search_params"]
    assert result["meta"]["search_params"]["ncode"] == "23"
    assert result["meta"]["search_params"]["status"] == "active"


def test_live_provider_does_not_invent_a_country_filter_for_us_targeting():
    requested: list = []
    client = httpx.Client(transport=httpx.MockTransport(_empty_handler(requested)))
    provider = LiveSAMGovProvider("secret", http_client=client)

    provider.list_projects({"limit": 5})

    # SAM documents only `state`/`zip` for location and has no country filter, so
    # US-only scoping is deliberately left to the qualification layer.
    params = requested[0]
    assert "country" not in params
    assert "state" not in params


def test_explicit_caller_filters_override_the_targeting_defaults():
    requested: list = []
    client = httpx.Client(transport=httpx.MockTransport(_empty_handler(requested)))
    provider = LiveSAMGovProvider("secret", http_client=client)

    provider.list_projects({"naics": "236220", "status": "inactive", "state": "CA", "ptype": "o", "limit": 5})

    params = requested[0]
    assert params["ncode"] == "236220"
    assert params["status"] == "inactive"
    assert params["state"] == "CA"
    assert params["ptype"] == "o"


def test_live_provider_pages_only_until_the_candidate_target():
    requested: list = []
    client = httpx.Client(transport=httpx.MockTransport(_paged_handler(10, 500, requested)))
    provider = LiveSAMGovProvider(
        "secret", http_client=client, max_pages=10, target_candidates=20, max_candidates=100
    )

    result = provider.list_projects({"limit": 100})

    # Page one asks for the caller's limit; page two is clamped to the 10
    # candidates still needed, and no third page is requested.
    assert [params["limit"] for params in requested] == ["100", "10"]
    assert [params["offset"] for params in requested] == ["0", "100"]
    assert len(result["projects"]) == 20
    assert result["meta"]["pages_fetched"] == 2
    assert result["meta"]["target_reached"] is True
    assert result["meta"]["target_candidates"] == 20


def test_live_provider_never_returns_more_than_the_hard_candidate_cap():
    requested: list = []
    client = httpx.Client(transport=httpx.MockTransport(_paged_handler(50, 5000, requested)))
    provider = LiveSAMGovProvider(
        "secret", http_client=client, max_pages=10, target_candidates=500, max_candidates=25
    )

    result = provider.list_projects({"limit": 100})

    # An over-large target is clamped to the hard ceiling, and the single
    # oversized page is trimmed instead of being paged further.
    assert provider.target_candidates == 25
    assert len(result["projects"]) == 25
    assert result["meta"]["max_candidates"] == 25
    assert result["meta"]["pagination_truncated"] is True
    assert len(requested) == 1


def test_live_provider_does_not_walk_the_whole_result_set():
    requested: list = []
    client = httpx.Client(transport=httpx.MockTransport(_paged_handler(20, 100_000, requested)))
    provider = LiveSAMGovProvider("secret", http_client=client)

    result = provider.list_projects({"limit": 20})

    assert result["meta"]["target_candidates"] == DEFAULT_TARGET_CANDIDATES == 20
    assert result["meta"]["max_candidates"] == HARD_MAX_CANDIDATES
    assert result["meta"]["pages_fetched"] == 1
    assert len(requested) == 1


def test_live_provider_still_respects_the_page_budget_when_a_page_comes_back_short():
    requested: list = []
    client = httpx.Client(transport=httpx.MockTransport(_paged_handler(1, 9_000, requested)))
    provider = LiveSAMGovProvider("secret", http_client=client, max_pages=3, target_candidates=20)

    result = provider.list_projects({"limit": 1})

    assert len(requested) == 3
    assert result["meta"]["pages_fetched"] == 3
    assert result["meta"]["pagination_truncated"] is True
    assert result["meta"]["target_reached"] is False


def test_live_provider_still_propagates_upstream_http_errors():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = LiveSAMGovProvider("secret", http_client=client, max_retries=0)

    with pytest.raises(httpx.HTTPStatusError):
        provider.list_projects({"limit": 5})


def test_live_provider_still_raises_when_rate_limit_retries_run_out():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(429, headers={"Retry-After": "0"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = LiveSAMGovProvider("secret", http_client=client, max_retries=1, retry_backoff_seconds=0)

    with pytest.raises(SAMGovRateLimitError):
        provider.list_projects({"limit": 5})
    assert attempts == 2


def test_live_provider_preserves_the_raw_record_and_source_identity():
    raw = {
        "noticeId": "N-1",
        "solicitationNumber": "W912-26-R-0001",
        "title": "Construction of Sidewalks and Curb Repair",
        "naicsCode": "236220",
        "type": "Solicitation",
        "placeOfPerformance": {"city": "Oakland", "state": "CA", "country": "USA"},
        "uiLink": "https://sam.gov/opp/N-1",
        "resourceLinks": [{"url": "https://example.test/plan-set.pdf"}],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"totalRecords": 1, "limit": 1, "offset": 0, "opportunitiesData": [raw]},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = LiveSAMGovProvider("secret", http_client=client)

    result = provider.list_projects({"limit": 1})

    row = result["projects"][0]
    assert row["source"] == "samgov"
    # The source payload survives field for field so ingestion keeps building
    # provenance from it.
    for key, value in raw.items():
        assert row[key] == value
    assert row["placeOfPerformance"]["country"] == "USA"
    assert result["meta"]["synthetic"] is False
    assert result["meta"]["live"] is True


def test_live_provider_carries_a_numeric_retry_after_on_rate_limit():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "120"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = LiveSAMGovProvider("secret", http_client=client, max_retries=0)

    before = datetime.now(timezone.utc)
    with pytest.raises(SAMGovRateLimitError) as caught:
        provider.list_projects({"limit": 5})

    retry_after = caught.value.retry_after
    assert retry_after is not None
    assert before + timedelta(seconds=119) <= retry_after <= before + timedelta(seconds=121)


def test_live_provider_carries_an_http_date_retry_after_on_rate_limit():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = LiveSAMGovProvider("secret", http_client=client, max_retries=0)

    with pytest.raises(SAMGovRateLimitError) as caught:
        provider.list_projects({"limit": 5})

    assert caught.value.retry_after == datetime(2026, 10, 21, 7, 28, tzinfo=timezone.utc)


def test_live_provider_reports_no_retry_after_when_the_header_is_missing():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = LiveSAMGovProvider("secret", http_client=client, max_retries=0)

    with pytest.raises(SAMGovRateLimitError) as caught:
        provider.list_projects({"limit": 5})

    # No reset time is invented when SAM.gov gave none.
    assert caught.value.retry_after is None


def test_live_provider_reports_no_retry_after_when_the_header_is_unparseable():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "soon-ish"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = LiveSAMGovProvider("secret", http_client=client, max_retries=0)

    with pytest.raises(SAMGovRateLimitError) as caught:
        provider.list_projects({"limit": 5})

    assert caught.value.retry_after is None


def test_live_provider_rate_limit_error_keeps_its_previous_message_and_type():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = LiveSAMGovProvider("secret", http_client=client, max_retries=0)

    with pytest.raises(SAMGovRateLimitError) as caught:
        provider.list_projects({"limit": 5})

    assert isinstance(caught.value, RuntimeError)
    assert str(caught.value) == "SAM.gov API rate limit reached after bounded retries"


def test_live_provider_rejects_an_invalid_candidate_budget():
    with pytest.raises(ValueError):
        LiveSAMGovProvider("secret", target_candidates=0)
    with pytest.raises(ValueError):
        LiveSAMGovProvider("secret", max_candidates=0)


def test_fixture_opportunity_provider_is_unaffected_by_live_targeting():
    result = SAMGovProvider().list_projects()

    assert result["meta"]["source"] == "samgov"
    assert "search_params" not in result["meta"]
    assert result["projects"]
