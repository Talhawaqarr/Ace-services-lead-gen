from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.models.core import Project


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


def qualifies_opportunity(project: Project, *, now: datetime | None = None, active_only: bool = True, construction_only: bool = True, deadline_within_days: int | None = None) -> bool:
    if active_only and str(project.status or "").upper() != "ACTIVE":
        return False
    if construction_only and construction_relevance(project) != "likely":
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
