from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.matching.engine import MATCHER_VERSION
from src.models.core import Contractor, MatchRecord, MatchReviewAudit, Project

VALID_STATUSES = {"UNREVIEWED", "APPROVED", "REJECTED", "SKIPPED"}
VALID_TRANSITIONS = {
    "UNREVIEWED": {"APPROVED", "REJECTED", "SKIPPED"},
    "APPROVED": {"REJECTED", "SKIPPED"},
    "REJECTED": {"APPROVED", "SKIPPED"},
    "SKIPPED": {"APPROVED", "REJECTED"},
}


def _coerce_uuid(value: Any, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} is required")
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError):
        raise ValueError(f"Invalid {field_name}: {value}")


def _validate_status(value: str) -> str:
    normalized = str(value).upper()
    if normalized not in VALID_STATUSES:
        raise ValueError(f"Invalid review status: {value}")
    return normalized


def list_matches_for_project(session: Session, project_id: str) -> list[MatchRecord]:
    valid_project_id = _coerce_uuid(project_id, "project_id")
    return session.execute(select(MatchRecord).where(MatchRecord.project_id == valid_project_id).order_by(MatchRecord.ranking.asc())).scalars().all()


def get_match(session: Session, match_id: str) -> MatchRecord:
    valid_match_id = _coerce_uuid(match_id, "match_id")
    match = session.get(MatchRecord, valid_match_id)
    if match is None:
        raise ValueError(f"Match not found: {match_id}")
    return match


def set_review_status(session: Session, match_id: str, new_status: str, actor: str = "local-dev", source: str = "local-dev") -> MatchRecord:
    match = get_match(session, match_id)
    normalized = _validate_status(new_status)
    previous_status = match.review_status or "UNREVIEWED"
    if previous_status == normalized:
        return match
    if normalized not in VALID_TRANSITIONS.get(previous_status, set()):
        raise ValueError(f"Invalid transition: {previous_status} -> {normalized}")
    match.review_status = normalized
    match.reviewed_at = datetime.utcnow()
    match.updated_at = datetime.utcnow()
    audit = MatchReviewAudit(
        match_id=match.id,
        previous_status=previous_status,
        new_status=normalized,
        actor=actor,
        source=source,
    )
    session.add(audit)
    session.flush()
    return match


def _ensure_project_row(session: Session, project: dict[str, Any]) -> str:
    project_id = project.get("id") or project.get("source_id") or str(uuid.uuid4())
    normalized_project_id = _coerce_uuid(project_id, "project_id")

    existing_by_id = session.get(Project, uuid.UUID(normalized_project_id))
    if existing_by_id is not None:
        return str(existing_by_id.id)

    source = project.get("source", "synthetic")
    source_id = project.get("source_id") or normalized_project_id
    existing = session.execute(
        select(Project).where(Project.source == source, Project.source_id == source_id)
    ).scalar_one_or_none()
    if existing is not None:
        return str(existing.id)

    project_record = Project(
        id=uuid.UUID(normalized_project_id),
        name=project.get("name") or "Unknown project",
        source=source,
        source_id=source_id,
        city=project.get("city"),
        state=project.get("state"),
        latitude=project.get("latitude"),
        longitude=project.get("longitude"),
        trades=project.get("trades"),
        bid_date=project.get("bid_date"),
        estimated_value=project.get("estimated_value"),
        provenance=project.get("provenance", {"source": source}),
    )
    session.add(project_record)
    session.flush()
    return str(project_record.id)


def _ensure_contractor_row(session: Session, contractor: dict[str, Any]) -> str:
    contractor_id = contractor.get("id") or contractor.get("source_id") or str(uuid.uuid4())
    normalized_contractor_id = _coerce_uuid(contractor_id, "contractor_id")
    existing_by_id = session.get(Contractor, uuid.UUID(normalized_contractor_id))
    if existing_by_id is not None:
        return str(existing_by_id.id)

    source = contractor.get("source", "synthetic")
    source_id = contractor.get("source_id") or normalized_contractor_id
    existing = session.execute(
        select(Contractor).where(Contractor.source == source, Contractor.source_id == source_id)
    ).scalar_one_or_none()
    if existing is not None:
        return str(existing.id)

    contractor_record = Contractor(
        id=uuid.UUID(normalized_contractor_id),
        company_name=contractor.get("company_name") or contractor.get("normalized_name") or "Unknown contractor",
        normalized_name=contractor.get("normalized_name") or contractor.get("company_name") or "Unknown contractor",
        source=source,
        source_id=source_id,
        city=contractor.get("city"),
        state=contractor.get("state"),
        trades=contractor.get("trades"),
        primary_email=contractor.get("primary_email"),
        provenance=contractor.get("provenance", {"source": source}),
    )
    session.add(contractor_record)
    session.flush()
    return str(contractor_record.id)


def create_match_record(session: Session, result: dict[str, Any]) -> MatchRecord:
    project_id = _coerce_uuid(result.get("project_id"), "project_id")
    contractor_id = _coerce_uuid(result.get("contractor_id"), "contractor_id")

    if session.get(Project, uuid.UUID(project_id)) is None:
        session.add(Project(
            id=uuid.UUID(project_id),
            name=result.get("project_name") or "Unknown project",
            source=result.get("project_source") or "synthetic",
            source_id=result.get("project_source_id") or project_id,
            city=result.get("project_city"),
            state=result.get("project_state"),
            latitude=result.get("project_latitude"),
            longitude=result.get("project_longitude"),
            trades=result.get("project_trades"),
            bid_date=result.get("project_bid_date"),
            estimated_value=result.get("project_estimated_value"),
            provenance=result.get("project_provenance", {"source": "synthetic"}),
        ))
        session.flush()

    if session.get(Contractor, uuid.UUID(contractor_id)) is None:
        session.add(Contractor(
            id=uuid.UUID(contractor_id),
            company_name=result.get("contractor_name") or "Unknown contractor",
            normalized_name=result.get("contractor_name") or "Unknown contractor",
            source=result.get("contractor_source") or "synthetic",
            source_id=result.get("contractor_source_id") or contractor_id,
            city=result.get("contractor_city"),
            state=result.get("contractor_state"),
            trades=result.get("contractor_trades"),
            primary_email=result.get("primary_email"),
            provenance=result.get("contractor_provenance", {"source": "synthetic"}),
        ))
        session.flush()

    existing = session.execute(
        select(MatchRecord).where(
            MatchRecord.project_id == project_id,
            MatchRecord.contractor_id == contractor_id,
            MatchRecord.matcher_version == result.get("matcher_version", MATCHER_VERSION),
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    record = MatchRecord(
        project_id=project_id,
        contractor_id=contractor_id,
        match_score=float(result.get("match_score", 0.0)),
        raw_score=float(result.get("raw_score", 0.0)),
        max_available_score=float(result.get("max_available_score", 0.0)),
        feature_completeness=float(result.get("feature_completeness", 0.0)),
        confidence=str(result.get("confidence", "LOW")),
        matcher_version=str(result.get("matcher_version", MATCHER_VERSION)),
        ranking=int(result.get("ranking", 0)),
        positive_factors=result.get("positive_factors", []),
        negative_factors=result.get("negative_factors", []),
        unknown_factors=result.get("unknown_factors", []),
        components=result.get("components", {}),
        review_status="UNREVIEWED",
    )
    session.add(record)
    session.flush()
    return record


def generate_matches(session: Session, project: dict[str, Any], contractors: Iterable[dict[str, Any]]) -> list[MatchRecord]:
    from src.matching.engine import match_project

    project_id = _ensure_project_row(session, project)
    project = dict(project)
    project["id"] = project_id
    project["source_id"] = project.get("source_id") or project_id

    normalized_contractors: list[dict[str, Any]] = []
    for contractor in contractors:
        contractor = dict(contractor)
        contractor["id"] = _ensure_contractor_row(session, contractor)
        contractor["source_id"] = contractor.get("source_id") or contractor["id"]
        normalized_contractors.append(contractor)

    results = match_project(project, normalized_contractors)
    persisted: list[MatchRecord] = []
    for result in results:
        result = dict(result)
        result["project_id"] = project_id
        result["contractor_id"] = _coerce_uuid(result.get("contractor_id"), "contractor_id")
        persisted.append(create_match_record(session, result))
    session.flush()
    return persisted
