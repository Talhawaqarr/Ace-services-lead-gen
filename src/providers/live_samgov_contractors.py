from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import httpx

from src.providers.contracts import ContractorProvider

ENTITY_INFORMATION_V3_URL = "https://api.sam.gov/entity-information/v3/entities"

# The Entity Management API serves the sections the contractor schema needs
# from two sections: identity/registration and the core business profile.
DEFAULT_INCLUDE_SECTIONS = "entityRegistration,coreData"

# The synchronous Entity Management API returns at most 10 records per page.
MAX_PAGE_SIZE = 10
ENTITY_REQUEST_FILTER_KEYS = {
    "primaryNaics",
    "naicsCode",
    "physicalAddressProvinceOrStateCode",
    "physicalAddressCity",
    "physicalAddressZipPostalCode",
    "physicalAddressCountryCode",
    "q",
}

# Only NAICS families the repository already models as trades are mapped.
# Anything else is preserved in provenance rather than forced into the runtime
# trade vocabulary.
NAICS_TRADE_MAP: tuple[tuple[tuple[str, ...], str], ...] = (
    (("236",), "general"),
    (("2381",), "roofing"),
    (("2382",), "concrete"),
    (("237", "221"), "civil"),
    (("5617",), "landscaping"),
)


class SAMEntityRateLimitError(RuntimeError):
    """Raised when the Entity API refuses a request after bounded retries."""


def _text(value: Any) -> str | None:
    if value is None or isinstance(value, (dict, list, tuple, set)):
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _normalize_entity_filters(filters: dict[str, Any] | None) -> dict[str, str]:
    if not isinstance(filters, dict):
        return {}
    normalized: dict[str, str] = {}
    for key, value in filters.items():
        if key not in ENTITY_REQUEST_FILTER_KEYS:
            continue
        if value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            cleaned = [str(item).strip() for item in value if str(item).strip()]
            if not cleaned:
                continue
            normalized[key] = cleaned[0]
            continue
        cleaned = str(value).strip()
        if cleaned:
            normalized[key] = cleaned
    return normalized


def _section(entity: dict[str, Any], name: str) -> dict[str, Any]:
    value = entity.get(name)
    return value if isinstance(value, dict) else {}


def _address_tokens(address: Any) -> tuple[str | None, str | None]:
    """Return (city, state) from an address object, tolerating partial shapes."""
    if not isinstance(address, dict):
        return None, None
    city = _text(address.get("city"))
    state = _text(address.get("stateOrProvinceCode")) or _text(address.get("stateCode"))
    return city, state


def _trades_from_naics(core_data: dict[str, Any]) -> list[str] | None:
    """Derive trades from the entity NAICS list using the repo's vocabulary."""
    naics_list = core_data.get("naicsList")
    if not isinstance(naics_list, list):
        return None

    entries = [entry for entry in naics_list if isinstance(entry, dict)]
    codes: list[str] = []
    for entry in entries:
        code = _text(entry.get("naicsCode"))
        if code:
            codes.append(code)
    if not codes:
        return None

    ordered_codes = list(codes)
    for entry in entries:
        if entry.get("isPrimary"):
            primary = _text(entry.get("naicsCode"))
            if primary:
                ordered_codes = [primary] + [code for code in codes if code != primary]
            break

    trades: list[str] = []
    for code in ordered_codes:
        for prefixes, trade in NAICS_TRADE_MAP:
            if code.startswith(prefixes):
                if trade not in trades:
                    trades.append(trade)
                break
    return trades or None


def _poc_email(core_data: dict[str, Any]) -> str | None:
    """Return a SAM point-of-contact email when the API exposes one.

    SAM Entity POC email is treated as potentially restricted/FOUO/CUI data and
    is not a general public company contact mailbox. The provider only maps what
    is explicitly supplied and does not invent an email when absent.
    """
    points = core_data.get("pointsOfContact")
    if not isinstance(points, list):
        return None
    for point in points:
        if isinstance(point, dict):
            email = _text(point.get("email"))
            if email:
                return email.lower()
    return None


def _normalize_entity(entity: dict[str, Any]) -> dict[str, Any] | None:
    """Map one Entity API record onto the existing contractor record shape."""
    registration = _section(entity, "entityRegistration")
    core_data = _section(entity, "coreData")

    company_name = _text(registration.get("legalBusinessName"))
    uei = _text(registration.get("ueiSAM"))
    if not company_name or not uei:
        # Without a stable UEI the record cannot be deduplicated, and without a
        # legal name there is nothing to display or match on.
        return None

    city, state = _address_tokens(core_data.get("physicalAddress"))
    naics_list = core_data.get("naicsList") if isinstance(core_data.get("naicsList"), list) else []

    business_types = core_data.get("businessTypes")
    return {
        "source": "sam_entity",
        "source_id": uei,
        "company_name": company_name,
        "city": city,
        "state": state,
        "trades": _trades_from_naics(core_data),
        "primary_email": _poc_email(core_data),
        "primary_phone": None,
        # The Entity API does not publish a company website field.
        "website": None,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "provenance": {
            "source": "sam_entity",
            "source_url": f"https://sam.gov/entity/{uei}",
            "entity_registration_status": _text(registration.get("ueiSAMStatus"))
            or _text(registration.get("status")),
            "entity_type": _text(core_data.get("entityType")),
            "business_types": business_types if isinstance(business_types, list) else [],
            "naics_codes": [
                _text(entry.get("naicsCode"))
                for entry in naics_list
                if isinstance(entry, dict) and _text(entry.get("naicsCode"))
            ],
            "mailing_city": _address_tokens(core_data.get("mailingAddress"))[0],
        },
    }


class LiveSAMEntityProvider(ContractorProvider):
    """Live SAM.gov Entity Information (Entity Management) API v3 provider.

    Returns public registration data only, and always issues a bounded number
    of pages so the contractor database is never downloaded.
    """

    source_name = "sam_entity"

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = ENTITY_INFORMATION_V3_URL,
        include_sections: str = DEFAULT_INCLUDE_SECTIONS,
        timeout: float = 30.0,
        http_client: httpx.Client | None = None,
        auto_paginate: bool = True,
        max_pages: int = 1,
        page_size: int = MAX_PAGE_SIZE,
        max_retries: int = 3,
        retry_backoff_seconds: float = 1.0,
        extra_params: dict[str, Any] | None = None,
    ):
        if not api_key or not api_key.strip():
            raise ValueError("SAMGOV_API_KEY is required for the live entity provider")
        if max_pages < 1:
            raise ValueError("max_pages must be >= 1")
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        self.api_key = api_key.strip()
        self.base_url = base_url
        self.include_sections = include_sections
        self.timeout = timeout
        self._client = http_client
        self.auto_paginate = auto_paginate
        self.max_pages = max_pages
        self.page_size = max(1, min(int(page_size), MAX_PAGE_SIZE))
        self.max_retries = max_retries
        self.retry_backoff_seconds = max(retry_backoff_seconds, 0.0)
        self.extra_params = dict(extra_params or {})

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
                        raise SAMEntityRateLimitError(
                            "SAM.gov Entity API rate limit reached after bounded retries"
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

            # Any non-2xx raises here rather than silently yielding no records.
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("SAM.gov Entity API returned a non-object response")
            if "entityData" not in payload:
                raise ValueError("SAM.gov Entity API response is missing entityData")
            return payload

    def _list_page(self, page_token: str | None, *, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            page = max(0, int(page_token)) if page_token is not None else 0
        except (TypeError, ValueError):
            page = 0

        params = {
            "includeSections": self.include_sections,
            "page": page,
            "size": self.page_size,
            **self.extra_params,
            **_normalize_entity_filters(filters),
        }
        payload = self._request(params)

        records = payload.get("entityData")
        if not isinstance(records, list):
            raise ValueError("SAM.gov Entity API entityData must be a list")

        contractors = []
        for record in records:
            if not isinstance(record, dict):
                continue
            normalized = _normalize_entity(record)
            if normalized is not None:
                contractors.append(normalized)

        next_page = page + 1 if len(records) >= self.page_size else None
        return {
            "contractors": contractors,
            "next_page_token": str(next_page) if next_page is not None else None,
            "meta": {
                "source": self.source_name,
                "live": True,
                "synthetic": False,
                "base_url": self.base_url,
                "include_sections": self.include_sections,
                "page": page,
                "page_size": self.page_size,
                "entity_records_returned": len(records),
            },
        }

    def list_contractors(
        self,
        filters: dict[str, Any] | None = None,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        # Supported parameters are the documented SAM.gov Entity filters. Unknown
        # keys are ignored so we do not guess a parameter contract.
        first = self._list_page(page_token, filters=filters)
        if not self.auto_paginate or page_token is not None:
            return first

        contractors = list(first["contractors"])
        meta = dict(first["meta"])
        next_token = first["next_page_token"]
        pages_fetched = 1
        truncated = False

        while next_token is not None:
            if pages_fetched >= self.max_pages:
                truncated = True
                break
            page = self._list_page(next_token, filters=filters)
            contractors.extend(page["contractors"])
            next_token = page["next_page_token"]
            pages_fetched += 1

        meta["pages_fetched"] = pages_fetched
        meta["records_returned"] = len(contractors)
        meta["pagination_truncated"] = truncated
        return {
            "contractors": contractors,
            "next_page_token": None,
            "meta": meta,
        }

    def get_contractor_details(self, source_id: str) -> dict[str, Any]:
        result = self.list_contractors()
        for row in result["contractors"]:
            if str(row.get("source_id")) == str(source_id):
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
                "include_sections": self.include_sections,
                "auto_paginate": self.auto_paginate,
                "max_pages": self.max_pages,
                "page_size": self.page_size,
            },
        }


__all__ = [
    "ENTITY_INFORMATION_V3_URL",
    "LiveSAMEntityProvider",
    "SAMEntityRateLimitError",
]

