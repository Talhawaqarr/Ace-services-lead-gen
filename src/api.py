from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
import httpx
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from src.config import get_settings
from src.db import SessionLocal
from src.ingestion.service import ingest_source_records
from src.models.core import Contractor, IngestionRun, MatchRecord, MatchReviewAudit, OutreachDraft, OutreachQueueItem, Project, RawProject
from src.providers.samgov import SAMGovProvider
from src.providers.live_samgov import LiveSAMGovProvider, SAMGovRateLimitError
from src.providers.usaspending import USASpendingProvider
from src.pipeline.service import (
    DEMO_HARD_MAX_RECORDS,
    _project_payload,
    discover_contractors,
    run_bounded_demo_pipeline,
    run_qualified_fixture_pipeline,
)
from src.review.service import generate_matches, set_review_status
from src.security import api_auth_middleware
from src.observability import configure_logging, request_logging_middleware
from src.opportunity.service import opportunity_payload, qualifies_opportunity
from src.outreach.service import build_outreach_draft, list_outreach_draft_audits, queue_approved_outreach, set_outreach_draft_status

configure_logging()
app = FastAPI(title="ACE Services Review API", version="0.6.0")
app.middleware("http")(api_auth_middleware)
app.middleware("http")(request_logging_middleware)
app.mount("/static", StaticFiles(directory=Path(__file__).resolve().parent / "static"), name="static")


class ReviewRequest(BaseModel):
    status: str
    actor: str | None = Field(default="local-dev")
    source: str | None = Field(default="local-dev")
    reason: str | None = None


class DemoRunRequest(BaseModel):
    """Bounded demo sync request.

    ``max_records`` is advisory only: the server always clamps it to
    DEMO_HARD_MAX_RECORDS. ``query`` may only carry a small allowlisted set of
    SAM.gov filter keys.
    """

    mode: Literal["fixture", "live"] = "fixture"
    max_records: int | None = Field(default=None, ge=1, le=1000)
    query: dict[str, str] | None = None
    deadline_within_days: int | None = Field(default=None, ge=1, le=365)


class ProjectSummary(BaseModel):
    id: str
    name: str
    source: str
    source_id: str
    city: str | None = None
    state: str | None = None
    bid_date: str | None = None
    posted_date: str | None = None
    response_deadline: str | None = None
    status: str | None = None
    description: str | None = None
    source_url: str | None = None
    estimated_value: float | None = None
    match_count: int = 0


class ContractorSummary(BaseModel):
    id: str
    company_name: str
    city: str | None = None
    state: str | None = None
    primary_email: str | None = None


class MatchEvidence(BaseModel):
    positive_factors: list[str] = []
    negative_factors: list[str] = []
    unknown_factors: list[str] = []
    components: dict[str, Any] = {}
    matcher_version: str


class MatchItem(BaseModel):
    id: str
    project_id: str
    contractor_id: str
    contractor_name: str
    contractor_email: str | None = None
    ranking: int
    match_score: float
    confidence: str
    review_status: str
    positive_factors: list[str] = []
    negative_factors: list[str] = []
    unknown_factors: list[str] = []
    components: dict[str, Any] = {}
    matcher_version: str


class ProjectWithMatches(BaseModel):
    project: dict[str, Any]
    matches: list[MatchItem]
    summary: dict[str, int]
    total: int
    limit: int
    offset: int


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    html_path = Path(__file__).resolve().parent / "templates" / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/config")
def runtime_config() -> dict[str, Any]:
    settings = get_settings()
    return {
        "app_env": settings.app_env,
        "ingestion_mode": settings.ingestion_mode,
        "email_provider": settings.email_provider,
        "llm_provider": settings.llm_provider,
        "dry_run": settings.dry_run,
        "max_emails_per_hour": settings.max_emails_per_hour,
        "samgov_api_key_configured": settings.samgov_api_key is not None,
        "samgov_page_limit": settings.samgov_page_limit,
        "samgov_max_pages": settings.samgov_max_pages,
    }



@app.get("/health/ready")
def readiness_check() -> dict[str, str]:
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        return {"status": "ready", "database": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc


@app.get("/projects", response_model=list[ProjectSummary])
def list_projects(limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0)) -> list[ProjectSummary]:
    with SessionLocal() as session:
        match_count = (
            select(func.count(MatchRecord.id))
            .where(MatchRecord.project_id == Project.id)
            .correlate(Project)
            .scalar_subquery()
        )
        rows = session.execute(
            select(Project, match_count.label("match_count"))
            .order_by(Project.name.asc())
            .offset(offset)
            .limit(limit)
        ).all()
        return [
            ProjectSummary(
                id=str(row.id),
                name=row.name,
                source=row.source,
                source_id=row.source_id,
                city=row.city,
                state=row.state,
                bid_date=row.bid_date,
                posted_date=row.posted_date,
                response_deadline=row.response_deadline,
                status=row.status,
                description=row.description,
                source_url=row.source_url,
                estimated_value=row.estimated_value,
                match_count=int(match_count_value),
            )
            for row, match_count_value in rows
        ]



@app.get("/opportunities", response_model=list[dict[str, Any]])
def list_opportunities(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    source: str | None = None,
    state: str | None = Query(default=None, min_length=2, max_length=2),
    active_only: bool = True,
    construction_only: bool = True,
    deadline_within_days: int | None = Query(default=None, ge=1, le=365),
) -> list[dict[str, Any]]:
    with SessionLocal() as session:
        query = select(Project).order_by(Project.response_deadline.asc().nullslast(), Project.name.asc())
        if source:
            query = query.where(Project.source == source.lower())
        if state:
            query = query.where(Project.state == state.upper())

        rows = session.execute(query).scalars().all()
        qualified = [
            row for row in rows
            if qualifies_opportunity(
                row,
                active_only=active_only,
                construction_only=construction_only,
                deadline_within_days=deadline_within_days,
            )
        ]
        return [opportunity_payload(row) for row in qualified[offset:offset + limit]]


@app.get("/contractors", response_model=list[ContractorSummary])
def list_contractors(limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0)) -> list[ContractorSummary]:
    with SessionLocal() as session:
        rows = session.execute(
            select(Contractor)
            .order_by(Contractor.company_name.asc())
            .offset(offset)
            .limit(limit)
        ).scalars().all()
        return [
            ContractorSummary(
                id=str(row.id),
                company_name=row.company_name,
                city=row.city,
                state=row.state,
            )
            for row in rows
        ]


@app.get("/projects/{project_id}", response_model=dict[str, Any])
def get_project(project_id: str) -> dict[str, Any]:
    with SessionLocal() as session:
        try:
            normalized = str(uuid.UUID(project_id))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid project id") from exc

        row = session.get(Project, uuid.UUID(normalized))
        if row is None:
            raise HTTPException(status_code=404, detail="Project not found")

        return {
            "id": str(row.id),
            "name": row.name,
            "source": row.source,
            "source_id": row.source_id,
            "city": row.city,
            "state": row.state,
            "latitude": row.latitude,
            "longitude": row.longitude,
            "trades": row.trades,
            "bid_date": row.bid_date,
            "posted_date": row.posted_date,
            "response_deadline": row.response_deadline,
            "status": row.status,
            "description": row.description,
            "source_url": row.source_url,
            "estimated_value": row.estimated_value,
            "provenance": row.provenance,
        }


@app.get("/projects/{project_id}/matches", response_model=ProjectWithMatches)
def get_project_matches(
    project_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    review_status: str | None = Query(default=None),
) -> ProjectWithMatches:
    with SessionLocal() as session:
        try:
            normalized = str(uuid.UUID(project_id))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid project id") from exc

        project_row = session.get(Project, uuid.UUID(normalized))
        if project_row is None:
            raise HTTPException(status_code=404, detail="Project not found")

        normalized_status = review_status.upper() if review_status else None
        valid_statuses = {"UNREVIEWED", "APPROVED", "REJECTED", "SKIPPED"}
        if normalized_status is not None and normalized_status not in valid_statuses:
            raise HTTPException(status_code=400, detail="Invalid review status")

        base_filters = [MatchRecord.project_id == uuid.UUID(normalized)]
        if normalized_status:
            base_filters.append(MatchRecord.review_status == normalized_status)

        total = session.execute(
            select(func.count(MatchRecord.id)).where(*base_filters)
        ).scalar_one()

        status_rows = session.execute(
            select(MatchRecord.review_status, func.count(MatchRecord.id))
            .where(MatchRecord.project_id == uuid.UUID(normalized))
            .group_by(MatchRecord.review_status)
        ).all()
        summary = {"total": 0, "unreviewed": 0, "approved": 0, "rejected": 0, "skipped": 0}
        for status, count in status_rows:
            key = status.lower() if status and status.lower() in {"approved", "rejected", "skipped"} else "unreviewed"
            summary[key] += int(count)
            summary["total"] += int(count)

        rows = session.execute(
            select(MatchRecord, Contractor)
            .join(Contractor, Contractor.id == MatchRecord.contractor_id)
            .where(*base_filters)
            .order_by(MatchRecord.ranking.asc(), MatchRecord.id.asc())
            .offset(offset)
            .limit(limit)
        ).all()

        match_items: list[MatchItem] = []
        for row, contractor in rows:
            match_items.append(
                MatchItem(
                    id=str(row.id),
                    project_id=str(row.project_id),
                    contractor_id=str(row.contractor_id),
                    contractor_name=contractor.company_name,
                    contractor_email=contractor.primary_email,
                    ranking=row.ranking,
                    match_score=float(row.match_score),
                    confidence=row.confidence,
                    review_status=row.review_status,
                    positive_factors=row.positive_factors or [],
                    negative_factors=row.negative_factors or [],
                    unknown_factors=row.unknown_factors or [],
                    components=row.components or {},
                    matcher_version=row.matcher_version,
                )
            )

        return ProjectWithMatches(
            project={
                "id": str(project_row.id),
                "name": project_row.name,
                "source": project_row.source,
                "source_id": project_row.source_id,
                "city": project_row.city,
                "state": project_row.state,
                "bid_date": project_row.bid_date,
                "posted_date": project_row.posted_date,
                "response_deadline": project_row.response_deadline,
                "status": project_row.status,
                "description": project_row.description,
                "source_url": project_row.source_url,
                "estimated_value": project_row.estimated_value,
                "construction_relevance": (
                    (project_row.provenance or {}).get("construction_relevance")
                    if isinstance(project_row.provenance, dict)
                    else None
                ),
            },
            matches=match_items,
            summary=summary,
            total=int(total),
            limit=limit,
            offset=offset,
        )


@app.get("/matches/{match_id}", response_model=dict[str, Any])
def get_match_detail(match_id: str) -> dict[str, Any]:
    with SessionLocal() as session:
        try:
            normalized = str(uuid.UUID(match_id))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid match id") from exc

        row = session.get(MatchRecord, uuid.UUID(normalized))
        if row is None:
            raise HTTPException(status_code=404, detail="Match not found")

        project = session.get(Project, row.project_id)
        contractor = session.get(Contractor, row.contractor_id)
        return {
            "id": str(row.id),
            "project_id": str(row.project_id),
            "contractor_id": str(row.contractor_id),
            "project": {
                "id": str(project.id) if project else None,
                "name": project.name if project else None,
                "city": project.city if project else None,
                "state": project.state if project else None,
                "bid_date": project.bid_date if project else None,
            },
            "contractor": {
                "id": str(contractor.id) if contractor else None,
                "company_name": contractor.company_name if contractor else None,
                "city": contractor.city if contractor else None,
                "state": contractor.state if contractor else None,
                "primary_email": contractor.primary_email if contractor else None,
            },
            "match": {
                "project_id": str(row.project_id),
                "contractor_id": str(row.contractor_id),
                "match_score": float(row.match_score),
                "confidence": row.confidence,
                "matcher_version": row.matcher_version,
                "ranking": row.ranking,
                "review_status": row.review_status,
                "raw_score": float(row.raw_score),
                "max_available_score": float(row.max_available_score),
            },
            "evidence": {
                "positive_factors": row.positive_factors or [],
                "negative_factors": row.negative_factors or [],
                "unknown_factors": row.unknown_factors or [],
                "components": row.components or {},
                "matcher_version": row.matcher_version,
            },
        }




@app.get("/matches/{match_id}/reviews", response_model=list[dict[str, Any]])
def list_match_reviews(match_id: str) -> list[dict[str, Any]]:
    with SessionLocal() as session:
        try:
            normalized = str(uuid.UUID(match_id))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid match id") from exc

        row = session.get(MatchRecord, uuid.UUID(normalized))
        if row is None:
            raise HTTPException(status_code=404, detail="Match not found")

        audits = session.execute(
            select(MatchReviewAudit)
            .where(MatchReviewAudit.match_id == row.id)
            .order_by(MatchReviewAudit.created_at.asc(), MatchReviewAudit.id.asc())
        ).scalars().all()

        return [
            {
                "id": str(audit.id),
                "match_id": str(audit.match_id),
                "previous_status": audit.previous_status,
                "new_status": audit.new_status,
                "actor": audit.actor,
                "source": audit.source,
                "created_at": audit.created_at.isoformat() if audit.created_at else None,
            }
            for audit in audits
        ]

class OutreachDraftResponse(BaseModel):
    id: str
    match_id: str
    template_version: str
    recipient_email: str
    subject: str
    body: str
    status: str
    generated_at: str | None = None
    approved_at: str | None = None
    approved_by: str | None = None
    provenance: dict[str, Any] = {}


def _outreach_draft_payload(draft: OutreachDraft) -> dict[str, Any]:
    return {
        "id": str(draft.id),
        "match_id": str(draft.match_id),
        "template_version": draft.template_version,
        "recipient_email": draft.recipient_email,
        "subject": draft.subject,
        "body": draft.body,
        "status": draft.status,
        "generated_at": draft.generated_at.isoformat() if draft.generated_at else None,
        "approved_at": draft.approved_at.isoformat() if draft.approved_at else None,
        "approved_by": draft.approved_by,
        "provenance": draft.provenance or {},
    }


@app.post("/matches/{match_id}/outreach-draft", response_model=OutreachDraftResponse)
def create_outreach_draft(match_id: str) -> OutreachDraftResponse:
    with SessionLocal() as session:
        try:
            normalized = str(uuid.UUID(match_id))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid match id") from exc

        try:
            draft = build_outreach_draft(session, normalized)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        session.commit()
        return OutreachDraftResponse(**_outreach_draft_payload(draft))


@app.get("/matches/{match_id}/outreach-draft", response_model=OutreachDraftResponse)
def get_outreach_draft(match_id: str) -> OutreachDraftResponse:
    with SessionLocal() as session:
        try:
            normalized = str(uuid.UUID(match_id))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid match id") from exc

        match = session.get(MatchRecord, uuid.UUID(normalized))
        if match is None:
            raise HTTPException(status_code=404, detail="Match not found")

        draft = session.execute(
            select(OutreachDraft)
            .where(OutreachDraft.match_id == match.id)
            .order_by(OutreachDraft.generated_at.desc(), OutreachDraft.id.desc())
        ).scalars().first()
        if draft is None:
            raise HTTPException(status_code=404, detail="Outreach draft not found")

        return OutreachDraftResponse(**_outreach_draft_payload(draft))



class OutreachQueueResponse(BaseModel):
    id: str
    draft_id: str
    recipient_email: str
    subject: str
    body: str
    status: str
    queued_at: str | None = None
    provenance: dict[str, Any] = {}


def _outreach_queue_payload(item: OutreachQueueItem) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "draft_id": str(item.draft_id),
        "recipient_email": item.recipient_email,
        "subject": item.subject,
        "body": item.body,
        "status": item.status,
        "queued_at": item.queued_at.isoformat() if item.queued_at else None,
        "provenance": item.provenance or {},
    }

@app.post("/outreach-drafts/{draft_id}/status", response_model=OutreachDraftResponse)
def update_outreach_draft_status(draft_id: str, payload: ReviewRequest) -> OutreachDraftResponse:
    with SessionLocal() as session:
        try:
            normalized = str(uuid.UUID(draft_id))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid draft id") from exc

        try:
            draft = set_outreach_draft_status(
                session,
                normalized,
                payload.status,
                actor=payload.actor or "local-dev",
                source=payload.source or "local-dev",
            )
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        session.commit()
        return OutreachDraftResponse(**_outreach_draft_payload(draft))



@app.post("/outreach-drafts/{draft_id}/queue", response_model=OutreachQueueResponse)
def queue_outreach_draft(draft_id: str) -> OutreachQueueResponse:
    with SessionLocal() as session:
        try:
            normalized = str(uuid.UUID(draft_id))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid draft id") from exc

        try:
            item = queue_approved_outreach(session, normalized)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        session.commit()
        return OutreachQueueResponse(**_outreach_queue_payload(item))

@app.get("/outreach-drafts/{draft_id}/reviews", response_model=list[dict[str, Any]])
def get_outreach_draft_reviews(draft_id: str) -> list[dict[str, Any]]:
    with SessionLocal() as session:
        try:
            normalized = str(uuid.UUID(draft_id))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid draft id") from exc

        try:
            audits = list_outreach_draft_audits(session, normalized)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        return [
            {
                "id": str(audit.id),
                "draft_id": str(audit.draft_id),
                "previous_status": audit.previous_status,
                "new_status": audit.new_status,
                "actor": audit.actor,
                "source": audit.source,
                "created_at": audit.created_at.isoformat() if audit.created_at else None,
            }
            for audit in audits
        ]


@app.post("/matches/{match_id}/review", response_model=dict[str, Any])
def review_match(match_id: str, payload: ReviewRequest) -> dict[str, Any]:
    with SessionLocal() as session:
        try:
            normalized = str(uuid.UUID(match_id))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid match id") from exc

        row = session.get(MatchRecord, uuid.UUID(normalized))
        if row is None:
            raise HTTPException(status_code=404, detail="Match not found")

        try:
            updated = set_review_status(session, str(row.id), payload.status, actor=payload.actor or "local-dev", source=payload.source or "local-dev")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        session.commit()
        return {
            "id": str(updated.id),
            "status": updated.review_status,
            "reviewed_at": updated.reviewed_at.isoformat() if updated.reviewed_at else None,
        }


@app.post("/projects/{project_id}/matches/generate")
def generate_project_matches(project_id: str) -> dict[str, Any]:
    with SessionLocal() as session:
        try:
            normalized = str(uuid.UUID(project_id))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid project id") from exc

        project_row = session.get(Project, uuid.UUID(normalized))
        if project_row is None:
            raise HTTPException(status_code=404, detail="Project not found")

        if not qualifies_opportunity(project_row):
            raise HTTPException(
                status_code=409,
                detail="Opportunity does not qualify for matching",
            )

        contractors = discover_contractors(session, project_row, source=project_row.source)
        project_payload = _project_payload(project_row)
        matches = generate_matches(session, project_payload, contractors)
        session.commit()
        return {"generated": len(matches), "project_id": str(project_row.id)}


@app.post("/pipeline/local/run")
def run_local_pipeline() -> dict[str, Any]:
    with SessionLocal() as session:
        summary = run_qualified_fixture_pipeline(session)
        session.commit()
        return summary


@app.get("/pipeline/demo/limits")
def demo_limits() -> dict[str, Any]:
    settings = get_settings()
    return {
        "hard_max_records": DEMO_HARD_MAX_RECORDS,
        "default_max_records": 5,
        "ingestion_mode": settings.ingestion_mode,
        "live_available": settings.ingestion_mode == "samgov",
        "samgov_api_key_configured": settings.samgov_api_key is not None,
    }


@app.post("/pipeline/demo/run")
def run_demo_pipeline(payload: DemoRunRequest | None = None) -> dict[str, Any]:
    """Run one bounded demo sync pass.

    The request is intentionally tiny: a small page of SAM.gov-shaped records
    is fetched, normalized, qualified, scored, and scoped to only the records
    touched by this run. The server enforces the maximum request size.
    """
    payload = payload or DemoRunRequest()
    with SessionLocal() as session:
        try:
            summary = run_bounded_demo_pipeline(
                session,
                mode=payload.mode,
                query=payload.query,
                max_records=payload.max_records,
                deadline_within_days=payload.deadline_within_days,
            )
            session.commit()
        except ValueError as exc:
            session.rollback()
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except SAMGovRateLimitError as exc:
            session.rollback()
            raise HTTPException(
                status_code=429,
                detail="SAM.gov API rate limit reached. No records were committed; wait for the quota reset before retrying.",
            ) from exc
        except httpx.HTTPStatusError as exc:
            session.rollback()
            raise HTTPException(
                status_code=502,
                detail=f"Upstream samgov API request failed with HTTP {exc.response.status_code}",
            ) from exc
        except Exception:
            session.rollback()
            raise
        return summary


@app.get("/outreach-queue", response_model=list[OutreachQueueResponse])
def list_outreach_queue() -> list[OutreachQueueResponse]:
    """List the demo outreach queue. Items are never delivered (NOT SENT)."""
    with SessionLocal() as session:
        rows = session.execute(
            select(OutreachQueueItem).order_by(OutreachQueueItem.queued_at.desc(), OutreachQueueItem.id.desc())
        ).scalars().all()
        return [OutreachQueueResponse(**_outreach_queue_payload(item)) for item in rows]


@app.get("/ingestion/sources")
def list_ingestion_sources() -> dict[str, Any]:
    return {
        "sources": [
            {
                "name": "usaspending",
                "type": "fixture-backed-public-source",
                "requires_credentials": False,
                "status": "local-only",
                "configured_mode": get_settings().ingestion_mode,
            },
            {
                "name": "samgov",
                "type": "official-public-api",
                "requires_credentials": True,
                "status": "live" if get_settings().ingestion_mode == "samgov" else "fixture",
                "live_integration_enabled": get_settings().ingestion_mode == "samgov",
                "page_limit": get_settings().samgov_page_limit,
                "max_pages": get_settings().samgov_max_pages,
            },
        ]
    }


@app.get("/ingestion/runs")
def list_ingestion_runs() -> list[dict[str, Any]]:
    with SessionLocal() as session:
        rows = session.execute(select(IngestionRun).order_by(IngestionRun.started_at.desc())).scalars().all()
        return [
            {
                "id": str(row.id),
                "source": row.source,
                "status": row.status,
                "started_at": row.started_at.isoformat() if row.started_at else None,
                "finished_at": row.finished_at.isoformat() if row.finished_at else None,
                "records_fetched": row.records_fetched,
                "accepted": row.accepted,
                "rejected": row.rejected,
                "duplicates": row.duplicates,
                "errors": row.errors,
            }
            for row in rows
        ]


@app.post("/ingestion/{source}/run")
def run_ingestion(source: str) -> dict[str, Any]:
    providers = {
        "usaspending": USASpendingProvider,
        "samgov": SAMGovProvider,
    }
    if source not in providers:
        raise HTTPException(status_code=404, detail="Unknown ingestion source")

    with SessionLocal() as session:
        provider = providers[source]()
        if source == "samgov" and get_settings().ingestion_mode == "samgov":
            settings = get_settings()
            provider = LiveSAMGovProvider(
                settings.samgov_api_key or "",
                max_pages=settings.samgov_max_pages,
            )
        try:
            summary = ingest_source_records(session, provider, source_name=source)
            session.commit()
        except SAMGovRateLimitError as exc:
            session.rollback()
            raise HTTPException(
                status_code=429,
                detail="SAM.gov API rate limit reached. No records were committed; wait for the quota reset before retrying.",
            ) from exc
        except httpx.HTTPStatusError as exc:
            session.rollback()
            raise HTTPException(
                status_code=502,
                detail=f"Upstream {source} API request failed with HTTP {exc.response.status_code}",
            ) from exc
        except Exception:
            session.rollback()
            raise
        summary["source"] = source
        return summary
