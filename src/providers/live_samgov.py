from __future__ import annotations

import time
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from src.providers.contracts import OpportunityProvider

# Search parameters verified against the official Contract Opportunities API
# documentation and recorded in docs/PHASE8_SAMGOV_ACCESS_AND_SCHEMA_VALIDATION.md:
#   ncode       NAICS code filter, applied here as the 23 construction category
#   status      accepts active / inactive / archived / cancelled / deleted
#   ptype       opportunity type, one documented code per request
#               (o = Solicitation, k = Combined Synopsis/Solicitation,
#                p = Pre-solicitation, s = Special Notice, r = Sources Sought,
#                a = Award Notice, g/u/i as documented)
#   state / zip place-of-performance filters
#   postedFrom / postedTo, limit (0-1000), offset
#
# Deliberate limitations -- no unverified parameter is invented for these, so
# they stay the job of src.opportunity.service.qualifies_opportunity:
#   * "US place of performance" cannot be requested. SAM documents only the
#     per-state `state` and `zip` filters; there is no country filter, and one
#     request per state would blow the request budget. A caller that wants a
#     single state can still pass `state`; US-wide scoping is enforced by
#     qualification on the persisted place-of-performance country.
#   * Notice-type exclusion is not requested. `ptype` takes a single documented
#     code and no multi-value syntax is verified, so narrowing to one code would
#     drop real solicitations (`o` vs `k`). Special Notice / Sources Sought /
#     RFI removal therefore stays with the qualification layer.
#   * "Active" is requested through `status=active`, but the API still returns
#     notices that later close, so qualification keeps re-checking `active`.
CONSTRUCTION_NAICS_CATEGORY = "23"
ACTIVE_STATUS = "active"

# Targeting defaults applied when a caller does not supply the filter itself.
TARGETING_DEFAULTS = {
    "ncode": CONSTRUCTION_NAICS_CATEGORY,
    "status": ACTIVE_STATUS,
}

# Candidate budget. `target_candidates` is how many construction candidates a
# run aims to return; `HARD_MAX_CANDIDATES` is the ceiling that no run can pass,
# so a live pass can never walk the whole SAM database.
DEFAULT_TARGET_CANDIDATES = 20
HARD_MAX_CANDIDATES = 100

# SAM documents `limit` as valid between 0 and 1000.
SAM_MAX_PAGE_LIMIT = 1000


def parse_retry_after(value: str | None) -> datetime | None:
    """Normalize an HTTP ``Retry-After`` value into an absolute UTC datetime.

    RFC 7231 allows two forms: delta-seconds (``"120"``) and an HTTP-date
    (``"Wed, 21 Oct 2026 07:28:00 GMT"``). A missing, malformed, or nonsensical
    value yields ``None``: a quota reset time is never invented, so a caller can
    distinguish "SAM told us when" from "SAM told us nothing".
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        seconds = float(text)
    except ValueError:
        pass
    else:
        if seconds < 0:
            return None
        return datetime.now(timezone.utc) + timedelta(seconds=seconds)
    try:
        parsed = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class SAMGovRateLimitError(RuntimeError):
    """Raised when SAM.gov refuses a request after bounded retries.

    ``retry_after`` is the absolute UTC instant SAM.gov asked us to wait until,
    taken from the ``Retry-After`` response header. It is ``None`` when SAM.gov
    sent no usable value, so callers must never treat a missing value as a reset
    time.
    """

    def __init__(self, message: str, *, retry_after: datetime | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class LiveSAMGovProvider(OpportunityProvider):
    """Live SAM.gov Contract Opportunities API provider.

    Uses the official public Contract Opportunities API. Search is targeted
    (NAICS construction category + active status + a posted-date window) so SAM
    returns construction candidates instead of an arbitrary first page.

    Retrieval is bounded on three axes: `target_candidates` stops paging as soon
    as enough candidates are collected, `max_candidates` is a hard ceiling that
    no run can exceed, and `max_pages` caps the number of requests. Page-token
    behavior is retained for callers that need exactly one page at a time.
    """

    source_name = "samgov"

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.sam.gov/opportunities/v2/search",
        timeout: float = 30.0,
        http_client: httpx.Client | None = None,
        auto_paginate: bool = True,
        max_pages: int = 100,
        max_retries: int = 3,
        retry_backoff_seconds: float = 1.0,
        target_candidates: int = DEFAULT_TARGET_CANDIDATES,
        max_candidates: int = HARD_MAX_CANDIDATES,
    ):
        if not api_key or not api_key.strip():
            raise ValueError("SAMGOV_API_KEY is required for the live provider")
        if max_pages < 1:
            raise ValueError("max_pages must be >= 1")
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if target_candidates < 1:
            raise ValueError("target_candidates must be >= 1")
        if max_candidates < 1:
            raise ValueError("max_candidates must be >= 1")
        self.api_key = api_key.strip()
        self.base_url = base_url
        self.timeout = timeout
        self._client = http_client
        self.auto_paginate = auto_paginate
        self.max_pages = max_pages
        self.max_retries = max_retries
        self.retry_backoff_seconds = max(retry_backoff_seconds, 0.0)
        # The target can never exceed the hard ceiling.
        self.max_candidates = max_candidates
        self.target_candidates = min(target_candidates, max_candidates)

    def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        request_params = {"api_key": self.api_key, **params}
        attempts = 0

        while True:
            try:
                if self._client is not None:
                    response = self._client.get(self.base_url, params=request_params)
                else:
                    with httpx.Client(timeout=self.timeout) as client:
                        response = client.get(self.base_url, params=request_params)
            except (httpx.TimeoutException, httpx.NetworkError):
                if attempts >= self.max_retries:
                    raise
                time.sleep(self.retry_backoff_seconds * (2**attempts))
                attempts += 1
                continue

            if response.status_code == 429 or 500 <= response.status_code < 600:
                if attempts >= self.max_retries:
                    if response.status_code == 429:
                        # Read Retry-After before raising: it is the only reset
                        # signal SAM.gov gives us, and it would otherwise be lost
                        # when the exception escapes the loop.
                        raise SAMGovRateLimitError(
                            "SAM.gov API rate limit reached after bounded retries",
                            retry_after=parse_retry_after(response.headers.get("Retry-After")),
                        )
                    response.raise_for_status()
                retry_after = response.headers.get("Retry-After")
                try:
                    delay = float(retry_after) if retry_after else self.retry_backoff_seconds * (2**attempts)
                except ValueError:
                    delay = self.retry_backoff_seconds * (2**attempts)
                time.sleep(max(delay, 0.0))
                attempts += 1
                continue

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

    def _list_page(
        self,
        filters: dict[str, Any],
        page_token: str | None,
        max_records: int | None = None,
    ) -> dict[str, Any]:
        posted_from, posted_to = self._date_range(filters)
        page_limit = min(max(int(filters.get("limit", 100)), 1), SAM_MAX_PAGE_LIMIT)
        if max_records is not None:
            # Never ask SAM for more than the candidates still needed.
            page_limit = min(page_limit, max(int(max_records), 1))
        params: dict[str, Any] = {
            "postedFrom": posted_from,
            "postedTo": posted_to,
            "limit": page_limit,
            "offset": max(int(page_token or filters.get("offset", 0)), 0),
        }

        mapping = {
            "keyword": "keyword",
            "state": "state",
            "naics": "ncode",
            "ptype": "ptype",
            "organization_id": "organizationId",
            "status": "status",
        }
        for source_key, api_key in mapping.items():
            value = filters.get(source_key)
            if value in (None, ""):
                # Construction category + active status when the caller did not
                # choose them, so a live pass is targeted instead of page one of
                # everything. An explicit caller filter always wins.
                value = TARGETING_DEFAULTS.get(api_key)
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
        next_offset = (
            offset + limit
            if isinstance(total, int) and offset + limit < total
            else None
        )

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
                "search_params": {
                    key: value
                    for key, value in sorted(params.items())
                    if key != "api_key"
                },
            },
        }

    def list_projects(
        self,
        filters: dict[str, Any] | None = None,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        filters = dict(filters or {})
        first = self._list_page(filters, page_token)
        if not self.auto_paginate or page_token is not None:
            return first

        projects = list(first["projects"])
        meta = dict(first["meta"])
        next_token = first["next_page_token"]
        pages_fetched = 1

        truncated = False
        target_reached = len(projects) >= self.target_candidates
        # Additional pages are fetched only to reach the candidate target, never
        # to exhaust the result set, so a run stays inside its request budget.
        while next_token is not None and not target_reached:
            if pages_fetched >= self.max_pages:
                truncated = True
                break
            remaining = self.target_candidates - len(projects)
            if remaining <= 0:
                target_reached = True
                break
            page = self._list_page(filters, next_token, max_records=remaining)
            projects.extend(page["projects"])
            next_token = page["next_page_token"]
            pages_fetched += 1
            target_reached = len(projects) >= self.target_candidates

        if len(projects) > self.max_candidates:
            # Hard ceiling: a single page can never push a run past it.
            projects = projects[: self.max_candidates]
            truncated = True
            next_token = None

        meta["pages_fetched"] = pages_fetched
        meta["records_returned"] = len(projects)
        meta["pagination_truncated"] = truncated
        meta["target_candidates"] = self.target_candidates
        meta["max_candidates"] = self.max_candidates
        meta["target_reached"] = len(projects) >= self.target_candidates
        return {
            "projects": projects,
            "next_page_token": None,
            "meta": meta,
        }

    def get_project_details(self, source_id: str) -> dict[str, Any]:
        # A detail lookup is a single bounded request: paging here would spend
        # the candidate budget on a lookup that only needs one row.
        result = self._list_page(
            {
                "keyword": source_id,
                "limit": 1,
                "posted_from": "01/01/2000",
                "posted_to": date.today(),
            },
            None,
        )
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
                "auto_paginate": self.auto_paginate,
                "max_pages": self.max_pages,
                "max_retries": self.max_retries,
                "target_candidates": self.target_candidates,
                "max_candidates": self.max_candidates,
                "naics_category": CONSTRUCTION_NAICS_CATEGORY,
                "status_filter": ACTIVE_STATUS,
            },
        }


__all__ = ["LiveSAMGovProvider", "SAMGovRateLimitError", "parse_retry_after"]
