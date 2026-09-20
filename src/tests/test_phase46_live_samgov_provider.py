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
    provider = LiveSAMGovProvider("secret", http_client=client)

    result = provider.list_projects(
        {"posted_from": "08/01/2026", "posted_to": "08/31/2026", "limit": 2}
    )

    assert result["projects"][0]["source"] == "samgov"
    assert result["projects"][0]["noticeId"] == "N-1"
    assert result["next_page_token"] == "2"
    assert result["meta"]["live"] is True


def test_live_provider_rejects_missing_api_key():
    try:
        LiveSAMGovProvider("")
    except ValueError as exc:
        assert "SAMGOV_API_KEY" in str(exc)
    else:
        raise AssertionError("expected ValueError")
