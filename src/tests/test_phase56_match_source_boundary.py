from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from src.api import app
from src.db import SessionLocal
from src.ingestion.service import ingest_source_records
from src.models.core import (
    Contractor,
    IngestionRun,
    MatchRecord,
    MatchReviewAudit,
    Project,
    RawProject,
)
from src.pipeline.service import contractor_source_for
from src.providers.live_samgov import LiveSAMGovProvider
from src.providers.samgov import SAMGovProvider

client = TestClient(app)

# A state no other suite seeds, so a stray row in the shared database can never
# enter the candidate pool and either hide or fake a cross-cohort match.
ISOLATION_STATE = "ND"


def _ingestion_run_ids() -> set[uuid.UUID]:
    session = SessionLocal()
    try:
        return {row.id for row in session.query(IngestionRun.id).all()}
    finally:
        session.close()


def _cleanup(token: str, *, runs_before: set[uuid.UUID] | None = None) -> None:
    session = SessionLocal()
    try:
        project_ids = [
            row.id
            for row in session.query(Project.id)
            .filter(Project.source == "samgov", Project.source_id.like(f"%{token}%"))
            .all()
        ]
        if project_ids:
            match_ids = [
                row.id
                for row in session.query(MatchRecord.id)
                .filter(MatchRecord.project_id.in_(project_ids))
                .all()
            ]
            if match_ids:
                session.query(MatchReviewAudit).filter(MatchReviewAudit.match_id.in_(match_ids)).delete(synchronize_session=False)
                session.query(MatchRecord).filter(MatchRecord.id.in_(match_ids)).delete(synchronize_session=False)
            session.query(Project).filter(Project.id.in_(project_ids)).delete(synchronize_session=False)
        session.query(RawProject).filter(RawProject.source_id.like(f"%{token}%")).delete(synchronize_session=False)
        session.query(Contractor).filter(Contractor.source_id.like(f"%{token}%")).delete(synchronize_session=False)
        if runs_before is not None:
            stale_runs = [row.id for row in session.query(IngestionRun.id).all() if row.id not in runs_before]
            if stale_runs:
                session.query(IngestionRun).filter(IngestionRun.id.in_(stale_runs)).delete(synchronize_session=False)
        session.commit()
    finally:
        session.close()


def _seed_project(token: str, *, live: bool, suffix: str) -> str:
    session = SessionLocal()
    try:
        project = Project(
            name=f"Phase 56 {'Live' if live else 'Fixture'} Opportunity {suffix}",
            source="samgov",
            source_id=f"phase56-{token}-{suffix}",
            city="Fargo",
            state=ISOLATION_STATE,
            trades=["general"],
            bid_date="2099-11-01",
            posted_date="2026-10-01T00:00:00Z",
            response_deadline="2099-12-31T17:00:00Z",
            status="ACTIVE",
            provenance={"construction_relevance": "likely", "synthetic": not live},
        )
        session.add(project)
        session.commit()
        return str(project.id)
    finally:
        session.close()


def _seed_contractor(token: str, *, source: str, suffix: str) -> str:
    source_id = f"phase56-{token}-{suffix.lower().replace(' ', '-')}"
    session = SessionLocal()
    try:
        contractor = Contractor(
            company_name=f"Phase 56 {suffix}",
            normalized_name=f"phase 56 {suffix.lower()}",
            source=source,
            source_id=source_id,
            city="Fargo",
            state=ISOLATION_STATE,
            trades=["general"],
        )
        session.add(contractor)
        session.commit()
        return source_id
    finally:
        session.close()


def _matches(project_id: str) -> list[dict]:
    """Return scoring plus cohort identity for every match on one project."""
    session = SessionLocal()
    try:
        rows = (
            session.query(
                MatchRecord.match_score,
                MatchRecord.raw_score,
                MatchRecord.max_available_score,
                MatchRecord.feature_completeness,
                MatchRecord.confidence,
                MatchRecord.matcher_version,
                MatchRecord.components,
                MatchRecord.positive_factors,
                MatchRecord.ranking,
                Contractor.source,
                Contractor.source_id,
            )
            .join(Contractor, MatchRecord.contractor_id == Contractor.id)
            .filter(MatchRecord.project_id == uuid.UUID(project_id))
            .all()
        )
        return [dict(row._mapping) for row in rows]
    finally:
        session.close()


def _generate(project_id: str):
    return client.post(f"/projects/{project_id}/matches/generate")


def test_live_opportunity_matches_only_live_entity_contractors():
    token = uuid.uuid4().hex
    project_id = _seed_project(token, live=True, suffix="live")
    _seed_contractor(token, source="sam_entity", suffix="Live Builder")
    _seed_contractor(token, source="samgov", suffix="Fixture Builder")
    try:
        response = _generate(project_id)

        assert response.status_code == 200
        assert response.json()["generated"] >= 1
        matched = _matches(project_id)
        matched_ids = {row["source_id"] for row in matched}
        # A live opportunity never sees a fixture samgov contractor, even though
        # the opportunity itself is stored with source "samgov".
        assert {row["source"] for row in matched} == {"sam_entity"}
        assert f"phase56-{token}-live-builder" in matched_ids
        assert f"phase56-{token}-fixture-builder" not in matched_ids
    finally:
        _cleanup(token)


def test_fixture_opportunity_matches_only_fixture_contractors():
    token = uuid.uuid4().hex
    project_id = _seed_project(token, live=False, suffix="fixture")
    _seed_contractor(token, source="samgov", suffix="Fixture Builder")
    _seed_contractor(token, source="sam_entity", suffix="Live Builder")
    try:
        response = _generate(project_id)

        assert response.status_code == 200
        assert response.json()["generated"] >= 1
        matched = _matches(project_id)
        matched_ids = {row["source_id"] for row in matched}
        assert {row["source"] for row in matched} == {"samgov"}
        assert f"phase56-{token}-fixture-builder" in matched_ids
        assert f"phase56-{token}-live-builder" not in matched_ids
    finally:
        _cleanup(token)


def test_match_generation_never_falls_back_across_the_boundary():
    live_token = uuid.uuid4().hex
    live_project = _seed_project(live_token, live=True, suffix="live")
    fixture_only = _seed_contractor(live_token, source="samgov", suffix="Fixture Only")
    try:
        response = _generate(live_project)
        assert response.status_code == 200
        # Before the fix this endpoint resolved contractors by project.source and
        # matched the live opportunity against the whole samgov pool.
        matched = _matches(live_project)
        assert "samgov" not in {row["source"] for row in matched}
        assert fixture_only not in {row["source_id"] for row in matched}
    finally:
        _cleanup(live_token)

    fixture_token = uuid.uuid4().hex
    fixture_project = _seed_project(fixture_token, live=False, suffix="fixture")
    live_only = _seed_contractor(fixture_token, source="sam_entity", suffix="Live Only")
    try:
        response = _generate(fixture_project)
        assert response.status_code == 200
        matched = _matches(fixture_project)
        assert "sam_entity" not in {row["source"] for row in matched}
        assert live_only not in {row["source_id"] for row in matched}
    finally:
        _cleanup(fixture_token)


def test_source_selection_leaves_scoring_and_evidence_unchanged():
    token = uuid.uuid4().hex
    live_project = _seed_project(token, live=True, suffix="live")
    fixture_project = _seed_project(token, live=False, suffix="fixture")
    _seed_contractor(token, source="sam_entity", suffix="Live Builder")
    _seed_contractor(token, source="samgov", suffix="Fixture Builder")
    try:
        assert _generate(live_project).status_code == 200
        assert _generate(fixture_project).status_code == 200

        live_rows = [
            row
            for row in _matches(live_project)
            if row["source_id"] == f"phase56-{token}-live-builder"
        ]
        fixture_rows = [
            row
            for row in _matches(fixture_project)
            if row["source_id"] == f"phase56-{token}-fixture-builder"
        ]
        assert len(live_rows) == 1
        assert len(fixture_rows) == 1
        live_match, fixture_match = live_rows[0], fixture_rows[0]

        # Only the cohort changes: identical project and contractor fields must
        # still score, rank and explain themselves identically.
        for key in (
            "match_score",
            "raw_score",
            "max_available_score",
            "feature_completeness",
            "confidence",
            "matcher_version",
            "ranking",
            "components",
            "positive_factors",
        ):
            assert live_match[key] == fixture_match[key], key
        assert live_match["match_score"] > 0
    finally:
        _cleanup(token)


class _StubOpportunityProvider:
    """Listing-only provider that declares its own origin metadata."""

    source_name = "samgov"

    def __init__(self, records, meta):
        self.records = records
        self.meta = meta

    def list_projects(self, filters=None, page_token=None):
        return {
            "projects": list(self.records),
            "next_page_token": None,
            "meta": dict(self.meta),
        }


def test_ingestion_persists_the_origin_marker_declared_by_each_provider():
    runs_before = _ingestion_run_ids()
    token = uuid.uuid4().hex

    live_record = {
        "source": "samgov",
        "source_id": f"phase56-{token}-live",
        "title": "Phase 56 Live Origin Fire Station",
        "active": True,
        "type": "Solicitation",
        "postedDate": "2026-10-01T00:00:00Z",
        "responseDeadLine": "2099-12-31T17:00:00Z",
        "placeOfPerformance": {"city": "Fargo", "state": ISOLATION_STATE, "country": "USA"},
        "naicsCode": "236220",
        "classificationCode": "M",
    }
    fixture_record = dict(
        live_record,
        source_id=f"phase56-{token}-fixture",
        title="Phase 56 Fixture Origin Fire Station",
    )

    session = SessionLocal()
    try:
        ingest_source_records(
            session,
            _StubOpportunityProvider([live_record], {"source": "samgov", "live": True, "synthetic": False}),
            source_name="samgov",
        )
        ingest_source_records(
            session,
            _StubOpportunityProvider([fixture_record], {"source": "samgov", "synthetic": True}),
            source_name="samgov",
        )
        session.commit()

        live = session.query(Project).filter(Project.source_id == f"phase56-{token}-live").one()
        fixture = session.query(Project).filter(Project.source_id == f"phase56-{token}-fixture").one()

        assert live.provenance["synthetic"] is False
        assert fixture.provenance["synthetic"] is True
        # The marker is what the endpoint reads, so each side lands in its cohort.
        assert contractor_source_for(live) == "sam_entity"
        assert contractor_source_for(fixture) == "samgov"

        # Both real providers declare exactly what ingestion consumes, so a real
        # fixture run and a real live run end up on opposite sides of the boundary.
        assert SAMGovProvider().health_check()["info"]["synthetic"] is True
        live_info = LiveSAMGovProvider("secret").health_check()["info"]
        assert live_info["live"] is True
        assert live_info["synthetic"] is False
    finally:
        session.close()
        _cleanup(token, runs_before=runs_before)


def test_contractor_source_for_defaults_to_fixture_and_keeps_other_sources():
    live = Project(name="Live", source="samgov", source_id="live", provenance={"synthetic": False})
    fixture = Project(name="Fixture", source="samgov", source_id="fixture", provenance={"synthetic": True})
    unmarked = Project(name="Unmarked", source="samgov", source_id="unmarked", provenance=None)
    other = Project(name="Other", source="phase29-qualified", source_id="other", provenance={})

    assert contractor_source_for(live) == "sam_entity"
    assert contractor_source_for(fixture) == "samgov"
    assert contractor_source_for(unmarked) == "samgov"
    assert contractor_source_for(other) == "phase29-qualified"

