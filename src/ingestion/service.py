from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.core import Contractor, IngestionRun, Project, RawContractor, RawProject


def _effective_source_id(raw: dict[str, Any]) -> str | None:
    if not isinstance(raw, dict):
        return None
    source = (raw.get("source") or "").strip().lower()
    if source == "samgov":
        solicitation = _normalized_text(raw.get("solicitationNumber"))
        if solicitation:
            return solicitation
    source_id = _normalized_text(raw.get("source_id") or raw.get("id") or raw.get("solicitationNumber") or raw.get("noticeid"))
    return source_id


def _effective_contractor_source_id(raw: dict[str, Any]) -> str | None:
    if not isinstance(raw, dict):
        return None
    source = (raw.get("source") or "").strip().lower()
    if source == "samgov":
        entity_id = _normalized_text(raw.get("entity_id") or raw.get("sam_id") or raw.get("entityId"))
        if entity_id:
            return entity_id
    return _normalized_text(raw.get("source_id") or raw.get("contractor_id") or raw.get("id"))


@dataclass
class IngestionSummary:
    source: str
    records_fetched: int
    accepted: int = 0
    rejected: int = 0
    duplicates: int = 0
    errors: int = 0
    created: int = 0
    updated: int = 0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalized_text(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned if cleaned else None


def _normalize_state(value: Any) -> str | None:
    cleaned = _normalized_text(value)
    if cleaned is None:
        return None
    return cleaned.upper()[:2]


def _normalize_city(value: Any) -> str | None:
    cleaned = _normalized_text(value)
    if cleaned is None:
        return None
    return cleaned.title()


def _normalize_active_status(value: Any) -> str | None:
    if isinstance(value, bool):
        return "ACTIVE" if value else "INACTIVE"
    cleaned = _normalized_text(value)
    if cleaned is None:
        return None
    normalized = cleaned.lower()
    if normalized in {"yes", "true", "1", "active"}:
        return "ACTIVE"
    if normalized in {"no", "false", "0", "inactive", "archived"}:
        return "INACTIVE"
    return cleaned


def _normalize_date(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned:
        return None
    return cleaned


def _normalize_numeric(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value).strip().replace(",", "")
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _derive_project_trades(raw: dict[str, Any]) -> list[str] | None:
    explicit = _normalize_trades(raw.get("trades") or raw.get("trade") or raw.get("project_type"))
    if explicit:
        return explicit

    naics = str(raw.get("naicsCode") or raw.get("naics_code") or "").strip()
    text = " ".join(
        str(raw.get(key) or "")
        for key in ("title", "description", "classificationCode")
    ).lower()

    if naics.startswith("236"):
        return ["general"]
    if naics.startswith(("237", "221")):
        return ["civil"]

    signal_map = (
        ("electrical", "electrical"),
        ("plumbing", "plumbing"),
        ("roofing", "roofing"),
        ("concrete", "concrete"),
        ("landscap", "landscaping"),
    )
    for token, trade in signal_map:
        if token in text:
            return [trade]
    return None


def _normalize_trades(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        parts = [value]
    elif isinstance(value, (list, tuple, set)):
        parts = list(value)
    else:
        return None
    cleaned = []
    for item in parts:
        text = _normalized_text(item)
        if text:
            cleaned.append(text.lower())
    return cleaned or None


def _build_raw_record(source: str, raw: dict[str, Any], status: str, error_detail: str | None = None) -> RawProject:
    return RawProject(
        source=source,
        source_id=_effective_source_id(raw) or "unknown",
        fetched_at=datetime.now(timezone.utc),
        raw_payload=raw,
        status=status,
        error_detail=error_detail,
    )


def _samgov_construction_relevance(raw: dict[str, Any]) -> str:
    text = " ".join([
        str(raw.get("title") or ""),
        str(raw.get("description") or ""),
        str(raw.get("naicsCode") or ""),
        str(raw.get("classificationCode") or ""),
        str(raw.get("type") or ""),
    ]).lower()
    construction_tokens = ["construction", "building", "renovation", "repair", "road", "bridge", "civil", "water", "wastewater", "fire station", "infrastructure", "facility", "project"]
    if raw.get("naicsCode") and str(raw.get("naicsCode")).startswith(("236", "237", "238", "221")):
        return "likely"
    if any(token in text for token in construction_tokens):
        return "likely"
    if raw.get("classificationCode") in {"M", "CIV", "CW", "B"}:
        return "likely"
    return "unlikely"


def _validate_samgov_dates(raw: dict[str, Any]) -> str | None:
    for key in ("postedDate", "reponseDeadLine"):
        value = raw.get(key)
        if value is None:
            continue
        cleaned = str(value).strip()
        if not cleaned:
            continue
        try:
            datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
        except ValueError:
            return f"Malformed SAM.gov date value for {key}: {value}"
    return None


def _project_record_for(raw: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    source = (raw.get("source") or "unknown").strip().lower()
    source_id = _effective_source_id(raw)
    if not source or not source_id:
        return {}, "Missing source or source_id"

    title = _normalized_text(raw.get("title") or raw.get("name"))
    if not title:
        return {}, "Missing project title"

    place = raw.get("placeOfPerformance") or {}
    state = _normalize_state((raw.get("state") or place.get("state") or (raw.get("location") or {}).get("state")))
    city = _normalize_city((raw.get("city") or place.get("city") or (raw.get("location") or {}).get("city")))
    posted_date = _normalize_date(raw.get("posted_date") or raw.get("postedDate"))
    response_deadline = _normalize_date(raw.get("response_deadline") or raw.get("responseDeadline") or raw.get("reponseDeadLine"))
    bid_date = _normalize_date(raw.get("bid_date") or raw.get("bidDate") or posted_date)
    raw_active = raw.get("active")
    status = _normalize_active_status(raw_active if raw_active is not None else raw.get("status"))
    if status is None and source != "samgov":
        status = _normalized_text(raw.get("type"))
    description = _normalized_text(raw.get("description"))
    source_url = _normalized_text(raw.get("uiLink") or raw.get("source_url"))
    estimated_value = _normalize_numeric(raw.get("estimated_value") or raw.get("estimatedValue"))
    trades = _derive_project_trades(raw)

    if raw.get("state") and len(str(raw.get("state"))) > 2:
        state = _normalize_state(raw.get("state").split()[0])

    if raw.get("bid_date") and str(raw.get("bid_date")).lower() in {"unknown", "n/a"}:
        bid_date = None

    if source == "samgov":
        date_error = _validate_samgov_dates(raw)
        if date_error:
            return {}, date_error

    normalized = {
        "id": str(raw.get("id") or source_id),
        "name": title,
        "source": source,
        "source_id": source_id,
        "city": city,
        "state": state,
        "latitude": raw.get("latitude"),
        "longitude": raw.get("longitude"),
        "trades": trades,
        "bid_date": bid_date,
        "posted_date": posted_date,
        "response_deadline": response_deadline,
        "status": status,
        "description": description,
        "source_url": source_url,
        "estimated_value": estimated_value,
        "provenance": {
            "source": source,
            "source_id": source_id,
            "raw_excerpt": title[:120],
            "source_url": raw.get("uiLink") or raw.get("source_url"),
            "response_deadline": raw.get("reponseDeadLine"),
            "posting_date": raw.get("postedDate"),
            "description": _normalized_text(raw.get("description")),
            "organization_name": _normalized_text(raw.get("organizationName")),
            "full_parent_path_name": _normalized_text(raw.get("fullParentPathName")),
            "procurement_type": _normalized_text(raw.get("type") or raw.get("baseType")),
            "naics_code": _normalized_text(raw.get("naicsCode")),
            "classification_code": _normalized_text(raw.get("classificationCode")),
            "resource_links": raw.get("resourceLinks") or [],
            "point_of_contact": raw.get("pointOfContact"),
            "award_amount": _normalize_numeric((raw.get("data") or {}).get("award", {}).get("amount")),
            "award_amount_source": "data.award.amount" if (raw.get("data") or {}).get("award", {}).get("amount") is not None else None,
            "construction_relevance": _samgov_construction_relevance(raw),
        },
    }

    if source == "samgov":
        normalized["provenance"]["source_id"] = source_id
        normalized["provenance"]["solicitation_number"] = _normalized_text(raw.get("solicitationNumber"))
        normalized["provenance"]["source_record_type"] = _normalized_text(raw.get("type") or raw.get("baseType"))

    if state is not None and len(state) != 2:
        return {}, "Invalid state value"
    return normalized, None


def _contractor_construction_relevance(raw: dict[str, Any]) -> str:
    entity_type = str(raw.get("entity_type") or raw.get("business_type") or raw.get("organization_type") or "").lower()
    name = str(raw.get("company_name") or raw.get("legal_name") or raw.get("name") or "").lower()
    trade_value = str(raw.get("trade") or raw.get("trades") or "").lower()
    if any(token in entity_type for token in ("housing", "authority", "government", "nonprofit", "association")):
        return "heuristic: likely not construction"
    if any(token in name for token in ("housing authority", "city of ", "county of ", "public agency", "nonprofit")):
        return "heuristic: likely not construction"
    if "construction" in trade_value or "general" in trade_value or "electrical" in trade_value or "civil" in trade_value:
        return "heuristic: likely construction"
    return "heuristic: unknown"


def _contractor_record_for(raw: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    if not isinstance(raw, dict):
        return {}, "Contractor record must be an object"

    source = (raw.get("source") or "unknown").strip().lower()
    source_id = _effective_contractor_source_id(raw)
    if not source or not source_id:
        return {}, "Missing source or source_id"

    company_name = _normalized_text(raw.get("company_name") or raw.get("legal_name") or raw.get("name") or raw.get("companyName"))
    if not company_name:
        return {}, "Missing company name"

    location = raw.get("location") if isinstance(raw.get("location"), dict) else {}
    city = _normalize_city(raw.get("city") or location.get("city"))
    state = _normalize_state(raw.get("state") or location.get("state"))
    if raw.get("state") and len(str(raw.get("state"))) > 2:
        state = _normalize_state(str(raw.get("state")).split()[0])

    trades = _normalize_trades(raw.get("trades") or raw.get("trade") or raw.get("specialties") or raw.get("classifications"))
    contact = raw.get("contact") if isinstance(raw.get("contact"), dict) else {}
    email = _normalized_text(raw.get("primary_email") or raw.get("email") or contact.get("email"))
    if email:
        email = email.lower().strip()
    phone = _normalized_text(raw.get("primary_phone") or raw.get("phone") or contact.get("phone"))
    website = _normalized_text(raw.get("website") or raw.get("website_url") or contact.get("website"))

    raw_payload = dict(raw)
    normalized = {
        "id": str(raw.get("id") or source_id),
        "company_name": company_name,
        "normalized_name": company_name,
        "source": source,
        "source_id": source_id,
        "city": city,
        "state": state,
        "trades": trades,
        "primary_email": email,
        "primary_phone": phone,
        "website": website,
        "provenance": {
            "source": source,
            "source_id": source_id,
            "fetched_at": raw.get("fetched_at") or raw.get("captured_at") or raw.get("last_updated") or None,
            "source_url": raw.get("source_url") or raw.get("sourceUrl") or raw.get("website"),
            "source_record_type": raw.get("record_type") or raw.get("entity_type") or raw.get("organization_type"),
            "construction_relevance": _contractor_construction_relevance(raw),
            "raw_payload": raw_payload,
            "notes": raw.get("notes"),
        },
    }

    if source == "samgov":
        normalized["provenance"]["samgov_entity_id"] = _normalized_text(raw.get("entity_id") or raw.get("sam_id") or raw.get("entityId"))

    if state is not None and len(state) != 2:
        return {}, "Invalid state value"
    return normalized, None


def ingest_source_records(
    session: Session,
    provider: Any,
    source_name: str | None = None,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    provider_filters: dict[str, Any] = dict(filters or {})
    if (source_name or getattr(provider, "source_name", "unknown")).strip().lower() == "samgov":
        # Keep live ingestion focused on construction and bounded to one page by default.
        from src.config import get_settings
        settings = get_settings()
        provider_filters = {
            "naics": "23",
            "limit": settings.samgov_page_limit,
            **provider_filters,
        }

    records = provider.list_projects(provider_filters) if hasattr(provider, "list_projects") else []
    payloads = records.get("projects", []) if isinstance(records, dict) else records

    source = source_name or getattr(provider, "source_name", "unknown")
    run = IngestionRun(
        source=source,
        started_at=datetime.now(timezone.utc),
        status="RUNNING",
        records_fetched=len(payloads),
    )
    session.add(run)
    session.flush()

    summary = IngestionSummary(
        source=source,
        records_fetched=len(payloads),
        accepted=0,
        rejected=0,
        duplicates=0,
        errors=0,
        created=0,
        updated=0,
    )

    for raw in payloads:
        source_id = _effective_source_id(raw) or str(raw.get("source_id") or raw.get("id") or "unknown")
        existing = session.execute(select(RawProject).where(RawProject.source == source, RawProject.source_id == source_id)).scalar_one_or_none()
        if existing is None:
            existing = _build_raw_record(source, raw, "RECEIVED")
            session.add(existing)
            session.flush()

        normalized, error = _project_record_for(raw)
        if error:
            existing.status = "REJECTED"
            existing.error_detail = error
            summary.rejected += 1
            summary.errors += 1
            session.flush()
            continue

        if source == "samgov" and _samgov_construction_relevance(raw) == "unlikely":
            existing.status = "REJECTED"
            existing.error_detail = "Opportunity does not meet construction relevance boundary"
            summary.rejected += 1
            session.flush()
            continue

        canonical = session.execute(select(Project).where(Project.source == source, Project.source_id == source_id)).scalar_one_or_none()
        if canonical is not None:
            existing.status = "DUPLICATE"
            existing.fetched_at = datetime.now(timezone.utc)
            existing.raw_payload = raw
            existing.error_detail = None
            summary.duplicates += 1

            # Source-derived fields are mutable. A notice can be amended after
            # first ingestion, so refresh them on subsequent syncs rather than
            # freezing the first observed version in the canonical record.
            canonical.name = normalized["name"]
            canonical.city = normalized.get("city")
            canonical.state = normalized.get("state")
            canonical.latitude = normalized.get("latitude")
            canonical.longitude = normalized.get("longitude")
            canonical.trades = normalized.get("trades")
            canonical.bid_date = normalized.get("bid_date")
            canonical.posted_date = normalized.get("posted_date")
            canonical.response_deadline = normalized.get("response_deadline")
            canonical.status = normalized.get("status")
            canonical.description = normalized.get("description")
            canonical.source_url = normalized.get("source_url")
            canonical.estimated_value = normalized.get("estimated_value")
            canonical.provenance = normalized.get("provenance")
            summary.updated += 1
            session.flush()
            continue

        project = Project(
            name=normalized["name"],
            source=normalized["source"],
            source_id=normalized["source_id"],
            city=normalized["city"],
            state=normalized["state"],
            latitude=normalized.get("latitude"),
            longitude=normalized.get("longitude"),
            trades=normalized.get("trades"),
            bid_date=normalized.get("bid_date"),
            posted_date=normalized.get("posted_date"),
            response_deadline=normalized.get("response_deadline"),
            status=normalized.get("status"),
            description=normalized.get("description"),
            source_url=normalized.get("source_url"),
            estimated_value=normalized.get("estimated_value"),
            provenance=normalized.get("provenance"),
        )
        session.add(project)
        existing.status = "ACCEPTED"
        existing.error_detail = None
        summary.accepted += 1
        summary.created += 1
        session.flush()

    run.status = "COMPLETED"
    run.finished_at = datetime.now(timezone.utc)
    run.accepted = summary.accepted
    run.rejected = summary.rejected
    run.duplicates = summary.duplicates
    run.errors = summary.errors
    session.add(run)
    return summary.as_dict()


def ingest_contractors(session: Session, provider: Any, source_name: str | None = None) -> dict[str, Any]:
    records = provider.list_contractors({}) if hasattr(provider, "list_contractors") else []
    payloads = records.get("contractors", []) if isinstance(records, dict) else records

    source = source_name or getattr(provider, "source_name", "unknown")
    run = IngestionRun(
        source=source,
        started_at=datetime.now(timezone.utc),
        status="RUNNING",
        records_fetched=len(payloads),
    )
    session.add(run)
    session.flush()

    summary = IngestionSummary(
        source=source,
        records_fetched=len(payloads),
        accepted=0,
        rejected=0,
        duplicates=0,
        errors=0,
        created=0,
        updated=0,
    )

    for raw in payloads:
        source_id = _effective_contractor_source_id(raw) or "unknown"
        existing = session.execute(select(RawContractor).where(RawContractor.source == source, RawContractor.source_id == source_id)).scalar_one_or_none()
        if existing is None:
            existing = RawContractor(
                source=source,
                source_id=source_id,
                fetched_at=datetime.now(timezone.utc),
                raw_payload=raw,
                status="RECEIVED",
            )
            session.add(existing)
            session.flush()

        normalized, error = _contractor_record_for(raw)
        if error:
            existing.status = "REJECTED"
            existing.error_detail = error
            summary.rejected += 1
            summary.errors += 1
            session.flush()
            continue

        canonical = session.execute(select(Contractor).where(Contractor.source == source, Contractor.source_id == source_id)).scalar_one_or_none()
        if canonical is not None:
            existing.status = "DUPLICATE"
            summary.duplicates += 1
            if canonical.company_name is None and normalized.get("company_name"):
                canonical.company_name = normalized["company_name"]
            if canonical.normalized_name is None and normalized.get("normalized_name"):
                canonical.normalized_name = normalized["normalized_name"]
            if canonical.city is None and normalized.get("city"):
                canonical.city = normalized["city"]
            if canonical.state is None and normalized.get("state"):
                canonical.state = normalized["state"]
            if canonical.trades in (None, []) and normalized.get("trades"):
                canonical.trades = normalized["trades"]
            if canonical.primary_email is None and normalized.get("primary_email"):
                canonical.primary_email = normalized["primary_email"]
            if canonical.primary_phone is None and normalized.get("primary_phone"):
                canonical.primary_phone = normalized["primary_phone"]
            if canonical.website is None and normalized.get("website"):
                canonical.website = normalized["website"]
            if canonical.provenance is None:
                canonical.provenance = normalized.get("provenance")
            session.flush()
            continue

        contractor = Contractor(
            company_name=normalized["company_name"],
            normalized_name=normalized["normalized_name"],
            source=normalized["source"],
            source_id=normalized["source_id"],
            city=normalized.get("city"),
            state=normalized.get("state"),
            trades=normalized.get("trades"),
            primary_email=normalized.get("primary_email"),
            primary_phone=normalized.get("primary_phone"),
            website=normalized.get("website"),
            provenance=normalized.get("provenance"),
        )
        session.add(contractor)
        existing.status = "ACCEPTED"
        existing.error_detail = None
        summary.accepted += 1
        summary.created += 1
        session.flush()

    run.status = "COMPLETED"
    run.finished_at = datetime.now(timezone.utc)
    run.accepted = summary.accepted
    run.rejected = summary.rejected
    run.duplicates = summary.duplicates
    run.errors = summary.errors
    session.add(run)
    return summary.as_dict()


__all__ = ["IngestionSummary", "ingest_contractors", "ingest_source_records"]
