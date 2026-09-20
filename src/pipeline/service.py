from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.ingestion.service import ingest_contractors, ingest_source_records
from src.models.core import Contractor, Project
from src.providers.samgov import SAMGovProvider
from src.providers.samgov_contractors import SAMGovContractorProvider
from src.review.service import generate_matches


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
    return [_contractor_payload(row) for row in rows]


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
