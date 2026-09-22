from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.ingestion.service import ingest_contractors, ingest_source_records
from src.models.core import Contractor, MatchRecord, Project
from src.opportunity.service import qualifies_opportunity
from src.providers.samgov import SAMGovProvider
from src.providers.samgov_contractors import SAMGovContractorProvider
from src.review.service import generate_matches

# Server-enforced ceiling for the bounded demo path. The client can request a
# smaller page but never a larger one. This keeps a demo run from accidentally
# harvesting every historical SAM.gov record in the database.
DEMO_HARD_MAX_RECORDS = 10
DEMO_DEFAULT_MAX_RECORDS = 5
DEMO_ALLOWED_QUERY_KEYS = frozenset({"keyword", "state", "naics", "ptype"})


def _project_payload(project: Project) -> dict[str, Any]:
    return {
        "id": str(project.id),
        "name": project.name,
        "source": project.source,
        "source_id": project.source_id,
        "city": project.city,
        "state": project.state,
        "latitude": project.latitude,
        "longitude": project.longitude,
        "trades": project.trades,
        "bid_date": project.bid_date,
        "estimated_value": project.estimated_value,
        "provenance": project.provenance,
    }


def _contractor_payload(contractor: Contractor) -> dict[str, Any]:
    return {
        "id": str(contractor.id),
        "company_name": contractor.company_name,
        "normalized_name": contractor.normalized_name,
        "source": contractor.source,
        "source_id": contractor.source_id,
        "city": contractor.city,
        "state": contractor.state,
        "trades": contractor.trades,
        "primary_email": contractor.primary_email,
        "provenance": contractor.provenance,
    }


def discover_contractors(
    session: Session,
    project: Project,
    source: str = "samgov",
) -> list[dict[str, Any]]:
    """Return canonical contractor candidates for a project.

    Discovery is deliberately non-scoring in Phase 12. Candidate selection comes
    from canonical contractor records; the deterministic matcher performs ranking
    and evidence generation afterward.
    """
    rows = session.execute(
        select(Contractor)
        .where(Contractor.source == source)
        .order_by(Contractor.company_name.asc(), Contractor.source_id.asc())
    ).scalars().all()

    project_state = str(project.state or "").strip().lower()
    project_trades = {
        str(value).strip().lower()
        for value in (project.trades or [])
        if str(value).strip()
    }

    candidates = []
    for row in rows:
        contractor_state = str(row.state or "").strip().lower()
        contractor_trades = {
            str(value).strip().lower()
            for value in (row.trades or [])
            if str(value).strip()
        }

        if project_state and contractor_state and project_state != contractor_state:
            continue
        if project_trades and contractor_trades and not project_trades.intersection(contractor_trades):
            continue

        candidates.append(row)

    return [_contractor_payload(row) for row in candidates]


def run_local_fixture_pipeline(
    session: Session,
    opportunity_provider: Any | None = None,
    contractor_provider: Any | None = None,
) -> dict[str, Any]:
    """Run the complete offline opportunity -> contractor -> match pipeline."""
    opportunity_provider = opportunity_provider or SAMGovProvider()
    contractor_provider = contractor_provider or SAMGovContractorProvider()

    opportunity_summary = ingest_source_records(
        session, opportunity_provider, source_name="samgov"
    )
    contractor_summary = ingest_contractors(
        session, contractor_provider, source_name="samgov"
    )

    projects = session.execute(
        select(Project)
        .where(Project.source == "samgov")
        .order_by(Project.name.asc(), Project.source_id.asc())
    ).scalars().all()

    generated = 0
    projects_processed = 0
    for project in projects:
        candidates = discover_contractors(session, project, source="samgov")
        if not candidates:
            continue
        matches = generate_matches(session, _project_payload(project), candidates)
        generated += len(matches)
        projects_processed += 1

    session.flush()

    return {
        "opportunities": opportunity_summary,
        "contractors": contractor_summary,
        "projects_discovered": len(projects),
        "projects_processed": projects_processed,
        "matches_generated": generated,
    }


def build_demo_filters(
    query: dict[str, Any] | None,
    *,
    max_records: int | None = None,
    hard_max: int = DEMO_HARD_MAX_RECORDS,
) -> tuple[dict[str, Any], int]:
    """Return server-bounded provider filters and the effective record cap.

    Client-supplied ``query`` may only contribute a small, allowlisted set of
    SAM.gov filter keys. The record count is always clamped to ``hard_max``
    regardless of what the caller asks for.
    """
    requested = max_records if max_records is not None else DEMO_DEFAULT_MAX_RECORDS
    try:
        requested_int = int(requested)
    except (TypeError, ValueError):
        requested_int = DEMO_DEFAULT_MAX_RECORDS
    effective_cap = max(1, min(requested_int, hard_max))

    filters: dict[str, Any] = {"limit": effective_cap}
    for key in DEMO_ALLOWED_QUERY_KEYS:
        value = (query or {}).get(key)
        if value in (None, ""):
            continue
        filters[key] = str(value).strip()
    return filters, effective_cap


def run_bounded_demo_pipeline(
    session: Session,
    *,
    mode: str = "fixture",
    query: dict[str, Any] | None = None,
    max_records: int | None = None,
    opportunity_provider: Any | None = None,
    contractor_provider: Any | None = None,
    deadline_within_days: int | None = None,
) -> dict[str, Any]:
    """Run one small, bounded demo pass of the offline/live workflow.

    The pass performs a tiny opportunity ingestion, normalizes the records,
    applies the existing construction qualification, discovers contractor
    candidates with the existing filtering, and generates deterministic
    matches -- but ONLY for the opportunities returned by THIS run. Historical
    SAM.gov rows already in the database are never re-scored here.
    """
    normalized_mode = (mode or "fixture").strip().lower()
    if normalized_mode not in {"fixture", "live"}:
        raise ValueError("Demo mode must be 'fixture' or 'live'")

    from src.config import get_settings

    settings = get_settings()
    filters, effective_cap = build_demo_filters(query, max_records=max_records)

    if opportunity_provider is None:
        if normalized_mode == "live":
            if settings.ingestion_mode != "samgov":
                raise ValueError(
                    "Live demo requires INGESTION_MODE=samgov with a configured SAM.gov API key"
                )
            if not settings.samgov_api_key:
                raise ValueError("Live demo requires a configured SAM.gov API key")
            # Imported lazily so the fixture path never requires httpx/network.
            from src.providers.live_samgov import LiveSAMGovProvider

            # Single-page, non-paginating request: server-enforced tiny budget.
            opportunity_provider = LiveSAMGovProvider(
                settings.samgov_api_key,
                auto_paginate=False,
                max_pages=1,
            )
        else:
            opportunity_provider = SAMGovProvider()

    if contractor_provider is None:
        contractor_provider = SAMGovContractorProvider()

    opportunity_summary = ingest_source_records(
        session,
        opportunity_provider,
        source_name="samgov",
        filters=filters,
    )
    contractor_summary = ingest_contractors(
        session,
        contractor_provider,
        source_name="samgov",
    )

    run_source_ids = list(dict.fromkeys(opportunity_summary.get("source_ids") or []))

    if not run_source_ids:
        session.flush()
        return {
            "mode": normalized_mode,
            "records_requested": effective_cap,
            "opportunities": opportunity_summary,
            "contractors": contractor_summary,
            "run_source_ids": [],
            "projects_discovered": 0,
            "qualified_projects": 0,
            "projects_processed": 0,
            "matches_generated": 0,
            "projects": [],
            "empty": True,
        }

    # Scope strictly to the records fetched by this run.
    projects = session.execute(
        select(Project)
        .where(Project.source == "samgov", Project.source_id.in_(run_source_ids))
        .order_by(Project.response_deadline.asc().nullslast(), Project.name.asc())
    ).scalars().all()

    qualified_ids = {
        project.id
        for project in projects
        if qualifies_opportunity(project, deadline_within_days=deadline_within_days)
    }

    generated = 0
    projects_processed = 0
    project_summaries: list[dict[str, Any]] = []

    for project in projects:
        is_qualified = project.id in qualified_ids
        project_match_count = 0
        generated_here = 0

        if is_qualified:
            candidates = discover_contractors(session, project, source="samgov")
            if candidates:
                matches = generate_matches(session, _project_payload(project), candidates)
                generated_here = len(matches)
                generated += generated_here
                projects_processed += 1
            project_match_count = session.execute(
                select(func.count(MatchRecord.id)).where(MatchRecord.project_id == project.id)
            ).scalar_one()

        project_summaries.append(
            {
                "id": str(project.id),
                "source_id": project.source_id,
                "name": project.name,
                "state": project.state,
                "city": project.city,
                "status": project.status,
                "response_deadline": project.response_deadline,
                "construction_relevance": (
                    (project.provenance or {}).get("construction_relevance")
                    if isinstance(project.provenance, dict)
                    else None
                ),
                "qualified": is_qualified,
                "matches_generated": generated_here,
                "match_count": int(project_match_count),
            }
        )

    session.flush()

    return {
        "mode": normalized_mode,
        "records_requested": effective_cap,
        "opportunities": opportunity_summary,
        "contractors": contractor_summary,
        "run_source_ids": run_source_ids,
        "projects_discovered": len(projects),
        "qualified_projects": len(qualified_ids),
        "projects_processed": projects_processed,
        "matches_generated": generated,
        "projects": project_summaries,
        "empty": False,
    }


def run_qualified_fixture_pipeline(
    session: Session,
    opportunity_provider: Any | None = None,
    contractor_provider: Any | None = None,
    *,
    deadline_within_days: int | None = None,
) -> dict[str, Any]:
    """Run the offline pipeline only for opportunities that pass qualification."""
    opportunity_provider = opportunity_provider or SAMGovProvider()
    contractor_provider = contractor_provider or SAMGovContractorProvider()

    opportunity_summary = ingest_source_records(
        session, opportunity_provider, source_name="samgov"
    )
    contractor_summary = ingest_contractors(
        session, contractor_provider, source_name="samgov"
    )

    projects = session.execute(
        select(Project)
        .where(Project.source == "samgov")
        .order_by(Project.response_deadline.asc().nullslast(), Project.name.asc())
    ).scalars().all()

    qualified = [
        project
        for project in projects
        if qualifies_opportunity(project, deadline_within_days=deadline_within_days)
    ]

    generated = 0
    projects_processed = 0
    for project in qualified:
        candidates = discover_contractors(session, project, source="samgov")
        if not candidates:
            continue
        matches = generate_matches(session, _project_payload(project), candidates)
        generated += len(matches)
        projects_processed += 1

    session.flush()

    return {
        "opportunities": opportunity_summary,
        "contractors": contractor_summary,
        "projects_discovered": len(projects),
        "qualified_projects": len(qualified),
        "projects_processed": projects_processed,
        "matches_generated": generated,
    }
