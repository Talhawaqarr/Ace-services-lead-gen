from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.core import Contractor


CONTACT_FIELDS = ("primary_email", "primary_phone", "website")
DEFAULT_SOURCE_PRIORITY = 0


def _source_priority(record: dict[str, Any], provider: Any) -> int:
    value = record.get("source_priority")
    if value is None:
        value = getattr(provider, "source_priority", DEFAULT_SOURCE_PRIORITY)
    try:
        return int(value)
    except (TypeError, ValueError):
        return DEFAULT_SOURCE_PRIORITY


def enrich_contractor(session: Session, contractor_id: Any, provider: Any) -> dict[str, Any]:
    contractor = session.execute(select(Contractor).where(Contractor.id == contractor_id)).scalar_one_or_none()
    if contractor is None:
        raise ValueError("Contractor not found")

    record = provider.enrich_contractor(contractor.source_id)
    if record is None:
        return {"status": "not_found", "contractor_id": str(contractor.id), "updated_fields": []}

    provider_name = record.get("source") or getattr(provider, "source_name", "unknown")
    incoming_priority = _source_priority(record, provider)
    provenance = dict(contractor.provenance or {})
    contact_sources = dict(provenance.get("contact_sources") or {})
    updated_fields: list[str] = []

    for field in CONTACT_FIELDS:
        value = record.get(field)
        if not value:
            continue
        normalized = str(value).strip().lower() if field == "primary_email" else str(value).strip()
        existing_source = contact_sources.get(field)
        existing_priority = DEFAULT_SOURCE_PRIORITY
        if isinstance(existing_source, dict):
            try:
                existing_priority = int(existing_source.get("priority", DEFAULT_SOURCE_PRIORITY))
            except (TypeError, ValueError):
                existing_priority = DEFAULT_SOURCE_PRIORITY

        if getattr(contractor, field) is None or incoming_priority > existing_priority:
            setattr(contractor, field, normalized)
            contact_sources[field] = {
                "source": provider_name,
                "priority": incoming_priority,
                "fetched_at": record.get("fetched_at") or datetime.now(timezone.utc).isoformat(),
            }
            updated_fields.append(field)

    history = list(provenance.get("enrichment_history") or [])
    history.append({
        "source": provider_name,
        "source_id": contractor.source_id,
        "fetched_at": record.get("fetched_at") or datetime.now(timezone.utc).isoformat(),
        "synthetic": bool(record.get("synthetic", False)),
        "source_priority": incoming_priority,
        "fields_found": [field for field in CONTACT_FIELDS if record.get(field)],
        "fields_updated": updated_fields,
    })
    provenance["contact_sources"] = contact_sources
    provenance["enrichment_history"] = history
    contractor.provenance = provenance
    session.flush()

    return {"status": "updated" if updated_fields else "no_change", "contractor_id": str(contractor.id), "updated_fields": updated_fields}


__all__ = ["CONTACT_FIELDS", "DEFAULT_SOURCE_PRIORITY", "enrich_contractor"]
