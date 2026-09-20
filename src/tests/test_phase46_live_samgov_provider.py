from __future__ import annotations

import httpx

from src.providers.live_samgov import LiveSAMGovProvider


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
