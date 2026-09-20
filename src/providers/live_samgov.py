from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import httpx

from src.providers.contracts import OpportunityProvider


class LiveSAMGovProvider(OpportunityProvider):
    """Live SAM.gov Contract Opportunities API provider.

    This provider uses the official public Contract Opportunities API rather than
    scraping SAM.gov. It is deliberately separate from the offline fixture provider.
    """

    source_name = "samgov"

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.sam.gov/opportunities/v2/search",
        timeout: float = 30.0,
        http_client: httpx.Client | None = None,
    ):
        if not api_key or not api_key.strip():
            raise ValueError("SAMGOV_API_KEY is required for the live provider")
        self.api_key = api_key.strip()
        self.base_url = base_url
        self.timeout = timeout
        self._client = http_client

    def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        request_params = {"api_key": self.api_key, **params}
        if self._client is not None:
            response = self._client.get(self.base_url, params=request_params)
        else:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(self.base_url, params=request_params)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("SAM.gov API returned a non-object response")
        return payload

    @staticmethod
    def _date_range(filters: dict[str, Any]) -> tuple[str, str]:
        posted_to = filters.get("posted_to") or date.today()
        posted_from = filters.get("posted_from") or (posted_to - timedelta(days=30))
        if isinstance(posted_from, date):
            posted_from = posted_from.strftime("%m/%d/%Y")
        if isinstance(posted_to, date):
            posted_to = posted_to.strftime("%m/%d/%Y")
        return str(posted_from), str(posted_to)

    def list_projects(
        self,
        filters: dict[str, Any] | None = None,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        filters = filters or {}
        posted_from, posted_to = self._date_range(filters)
        params: dict[str, Any] = {
            "postedFrom": posted_from,
            "postedTo": posted_to,
            "limit": min(max(int(filters.get("limit", 100)), 1), 1000),
            "offset": max(int(page_token or filters.get("offset", 0)), 0),
        }

        mapping = {
            "keyword": "keyword",
            "state": "state",
            "naics": "ncode",
            "ptype": "ptype",
            "organization_id": "organizationId",
        }
        for source_key, api_key in mapping.items():
            value = filters.get(source_key)
            if value not in (None, ""):
                params[api_key] = value

        payload = self._request(params)
        records = payload.get("opportunitiesData") or []
        if not isinstance(records, list):
            raise ValueError("SAM.gov API opportunitiesData must be a list")

        normalized = []
        for record in records:
            if not isinstance(record, dict):
                continue
            row = dict(record)
            row["source"] = self.source_name
            normalized.append(row)

        total = payload.get("totalRecords")
        limit = int(payload.get("limit") or params["limit"])
        offset = int(payload.get("offset") or params["offset"])
        next_offset = offset + limit if isinstance(total, int) and offset + limit < total else None

        return {
            "projects": normalized,
            "next_page_token": str(next_offset) if next_offset is not None else None,
            "meta": {
                "source": self.source_name,
                "synthetic": False,
                "live": True,
                "total_records": total,
                "offset": offset,
                "limit": limit,
                "posted_from": posted_from,
                "posted_to": posted_to,
            },
        }

    def get_project_details(self, source_id: str) -> dict[str, Any]:
        result = self.list_projects({"source_id": source_id, "limit": 1})
        for row in result["projects"]:
            solicitation = row.get("solicitationNumber") or row.get("source_id")
            notice_id = row.get("noticeId") or row.get("noticeid")
            if str(solicitation) == str(source_id) or str(notice_id) == str(source_id):
                return row
        raise KeyError(source_id)

    def health_check(self) -> dict[str, Any]:
        return {
            "status": "configured",
            "info": {
                "source": self.source_name,
                "live": True,
                "synthetic": False,
                "base_url": self.base_url,
            },
        }


__all__ = ["LiveSAMGovProvider"]
