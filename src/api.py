from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from src.config import get_settings
from src.db import SessionLocal
from src.ingestion.service import ingest_source_records
from src.models.core import Contractor, IngestionRun, MatchRecord, Project, RawProject
from src.providers.samgov import SAMGovProvider
from src.providers.usaspending import USASpendingProvider
from src.pipeline.service import run_local_fixture_pipeline
from src.review.service import generate_matches, set_review_status
from src.security import api_auth_middleware
from src.observability import configure_logging, request_logging_middleware

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


class ProjectSummary(BaseModel):
    id: str
    name: str
    source: str
    source_id: str
    city: str | None = None
    state: str | None = None
    bid_date: str | None = None
    estimated_value: float | None = None
    match_count: int = 0


class ContractorSummary(BaseModel):
    id: str
    company_name: str
    city: str | None = None
    state: str | None = None


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
                estimated_value=row.estimated_value,
                match_count=int(match_count_value),
            )
            for row, match_count_value in rows
        ]



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
            "estimated_value": row.estimated_value,
            "provenance": row.provenance,
        }


@app.get("/projects/{project_id}/matches", response_model=ProjectWithMatches)
def get_project_matches(project_id: str) -> ProjectWithMatches:
    with SessionLocal() as session:
        try:
            normalized = str(uuid.UUID(project_id))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid project id") from exc

        project_row = session.get(Project, uuid.UUID(normalized))
        if project_row is None:
            raise HTTPException(status_code=404, detail="Project not found")

        rows = session.execute(
            select(MatchRecord, Contractor)
            .join(Contractor, Contractor.id == MatchRecord.contractor_id)
            .where(MatchRecord.project_id == uuid.UUID(normalized))
            .order_by(MatchRecord.ranking.asc())
        ).all()

        summary = {"total": len(rows), "unreviewed": 0, "approved": 0, "rejected": 0, "skipped": 0}
        match_items: list[MatchItem] = []
        for row, contractor in rows:
            summary[row.review_status.lower() if row.review_status.lower() in {"approved", "rejected", "skipped"} else "unreviewed"] += 1
            match_items.append(
                MatchItem(
                    id=str(row.id),
                    project_id=str(row.project_id),
                    contractor_id=str(row.contractor_id),
                    contractor_name=contractor.company_name,
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
                "estimated_value": project_row.estimated_value,
            },
            matches=match_items,
            summary=summary,
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

        contractor_rows = session.execute(select(Contractor)).scalars().all()
        contractors = [{
            "id": str(row.id),
            "company_name": row.company_name,
            "normalized_name": row.normalized_name,
            "source": row.source,
            "source_id": row.source_id,
            "city": row.city,
            "state": row.state,
            "latitude": None,
            "longitude": None,
            "trades": row.trades,
        } for row in contractor_rows]

        project_payload = {
            "id": str(project_row.id),
            "name": project_row.name,
            "source": project_row.source,
            "source_id": project_row.source_id,
            "city": project_row.city,
            "state": project_row.state,
            "latitude": project_row.latitude,
            "longitude": project_row.longitude,
            "trades": project_row.trades,
            "bid_date": project_row.bid_date,
            "estimated_value": project_row.estimated_value,
        }
        matches = generate_matches(session, project_payload, contractors)
        session.commit()
        return {"generated": len(matches), "project_id": str(project_row.id)}


@app.post("/pipeline/local/run")
def run_local_pipeline() -> dict[str, Any]:
    with SessionLocal() as session:
        summary = run_local_fixture_pipeline(session)
        session.commit()
        return summary


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
                "type": "fixture-backed-source-contract",
                "requires_credentials": False,
                "status": "local-only",
                "live_integration_disabled": True,
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
        summary = ingest_source_records(session, provider, source_name=source)
        session.commit()
        summary["source"] = source
        return summary
