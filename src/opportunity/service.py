from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.models.core import Project


# ACE's contractor market is US construction, so a recorded NAICS code has to sit
# in the construction sector (23xxx). Title wording alone is not evidence: SAM.gov
# titles are written by contracting officers and routinely describe events such as
# an Industry Day, or non-construction work filed under a 23xxx code.
CONSTRUCTION_NAICS_PREFIX = "23"

# SAM.gov notice types that are never a contract solicitation. These are compared
# against the normalized notice type already stored in provenance, never against
# the notice title, so a genuine solicitation whose title happens to mention a
# topic stays eligible while a Special Notice/Industry Day/RFI event never does.
NON_SOLICITATION_NOTICE_TYPES = frozenset(
    {
        "industry day",
        "industry day conference",
        "industry day notice",
        "request for information",
        "request for information rfi",
        "reverse industry day",
        "rfi",
        "sources sought",
        "sources sought notice",
        "sources sought synopsis",
        "special notice",
    }
)

# Normalized place-of-performance country values that mean the United States.
# Compared space-insensitively so "USA", "U.S.A." and "United States of America"
# all collapse onto the same token.
US_COUNTRY_VALUES = frozenset({"us", "usa", "unitedstates", "unitedstatesofamerica"})

# Provenance keys written by src.ingestion.service._project_record_for. The
# snake_case keys are the project's normalized fields and the only source read
# here, so no raw payload is re-parsed during qualification.
NOTICE_TYPE_PROVENANCE_KEYS = ("procurement_type", "source_record_type")
NAICS_PROVENANCE_KEYS = ("naics_code",)
COUNTRY_PROVENANCE_KEYS = ("place_of_performance_country",)


def _normalize_label(value: Any) -> str:
    """Fold a source label into a comparable, punctuation-insensitive token.

    "Combined Synopsis/Solicitation", "U.S.A." and "RFI" all normalize without
    case or separator noise, so the rules below compare exact values instead of
    guessing with fuzzy substring matching.
    """
    if isinstance(value, dict):
        for key in ("Name", "name", "Code", "code"):
            nested = _normalize_label(value.get(key))
            if nested:
                return nested
        return ""
    if value is None:
        return ""
    cleaned: list[str] = []
    for character in str(value).lower():
        if character.isalnum():
            cleaned.append(character)
        elif character not in ".,'-_":
            cleaned.append(" ")
    return " ".join("".join(cleaned).split())


def _provenance_value(project: Project, keys: tuple[str, ...]) -> str:
    provenance = project.provenance if isinstance(project.provenance, dict) else {}
    for key in keys:
        label = _normalize_label(provenance.get(key))
        if label:
            return label
    return ""


def parse_opportunity_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def construction_relevance(project: Project) -> str:
    provenance = project.provenance if isinstance(project.provenance, dict) else {}
    value = provenance.get("construction_relevance")
    return str(value).lower() if value is not None else "unknown"


def notice_type(project: Project) -> str | None:
    """Normalized SAM.gov notice/base type, or None when none was reported."""
    return _provenance_value(project, NOTICE_TYPE_PROVENANCE_KEYS) or None


def naics_code(project: Project) -> str | None:
    """Normalized NAICS code, or None when the source did not report one."""
    return _provenance_value(project, NAICS_PROVENANCE_KEYS) or None


def place_of_performance_country(project: Project) -> str | None:
    """Normalized place-of-performance country, or None when none was reported."""
    return _provenance_value(project, COUNTRY_PROVENANCE_KEYS) or None


def is_solicitation_notice_type(value: str | None) -> bool:
    """False only for the enumerated non-solicitation notice types.

    An unreported notice type is accepted so a source that introduces a new
    contract-solicitation label is not silently dropped; the rejection is an
    explicit list, never title matching.
    """
    if value is None:
        return True
    return value not in NON_SOLICITATION_NOTICE_TYPES


def is_construction_naics(value: str | None) -> bool:
    """True when the reported NAICS code is construction-family (23xxx)."""
    if value is None:
        return True
    return value.startswith(CONSTRUCTION_NAICS_PREFIX)


def is_us_place_of_performance(value: str | None) -> bool:
    """True when place of performance is the US, or when no country was reported.

    The contracting office address is deliberately ignored here: a US-based
    office routinely issues notices whose performance happens abroad.
    """
    if value is None:
        return True
    return value.replace(" ", "") in US_COUNTRY_VALUES


def qualifies_opportunity(project: Project, *, now: datetime | None = None, active_only: bool = True, construction_only: bool = True, deadline_within_days: int | None = None) -> bool:
    if active_only and str(project.status or "").upper() != "ACTIVE":
        return False
    # Notice type and geography are absolute boundaries for the US contractor
    # market: a Special Notice is never a lead, and work performed abroad can
    # never be served by a US contractor roster.
    if not is_solicitation_notice_type(notice_type(project)):
        return False
    if not is_us_place_of_performance(place_of_performance_country(project)):
        return False
    if construction_only:
        if construction_relevance(project) != "likely":
            return False
        if not is_construction_naics(naics_code(project)):
            return False
    deadline = parse_opportunity_datetime(project.response_deadline)
    if deadline_within_days is not None:
        if deadline is None:
            return False
        reference = now or datetime.now(timezone.utc)
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=timezone.utc)
        delta_seconds = (deadline - reference).total_seconds()
        if delta_seconds < 0 or delta_seconds > deadline_within_days * 86400:
            return False
    return True


def opportunity_payload(project: Project) -> dict[str, Any]:
    return {
        "id": str(project.id), "name": project.name, "source": project.source,
        "source_id": project.source_id, "city": project.city, "state": project.state,
        "posted_date": project.posted_date, "response_deadline": project.response_deadline,
        "status": project.status, "description": project.description,
        "source_url": project.source_url, "construction_relevance": construction_relevance(project),
    }
