from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.core import Contractor


def enrich_contractor(session: Session, contractor_id: Any, provider: Any) -> dict[str, Any]:
    contractor = session.execute(select(Contractor).where(Contractor.id == contractor_id)).scalar_one_or_none()
    if contractor is None:
        raise ValueError("Contractor not found")

    record = provider.enrich_contractor(contractor.source_id)
    if record is None:
        return {"status": "not_found", "contractor_id": str(contractor.id), "updated_fields": []}

    updated_fields: list[str] = []
    for field in ("primary_email", "primary_phone", "website"):
        value = record.get(field)
        if getattr(contractor, field) is None and value:
            setattr(contractor, field, str(value).strip().lower() if field == "primary_email" else str(value).strip())
            updated_fields.append(field)

    provenance = dict(contractor.provenance or {})
    history = list(provenance.get("enrichment_history") or [])
    history.append({
        "source": record.get("source") or getattr(provider, "source_name", "unknown"),
        "source_id": contractor.source_id,
        "fetched_at": record.get("fetched_at") or datetime.now(timezone.utc).isoformat(),
        "synthetic": bool(record.get("synthetic", False)),
        "fields_found": [field for field in ("primary_email", "primary_phone", "website") if record.get(field)],
        "fields_updated": updated_fields,
    })
    provenance["enrichment_history"] = history
    contractor.provenance = provenance
    session.flush()

    return {"status": "updated" if updated_fields else "no_change", "contractor_id": str(contractor.id), "updated_fields": updated_fields}


__all__ = ["enrich_contractor"]
