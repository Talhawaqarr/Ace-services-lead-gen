from __future__ import annotations

import uuid

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from fastapi.testclient import TestClient

from src.api import app
from src.db import SessionLocal
from src.models.core import Contractor, Project


def test_phase21_canonical_tables_have_source_identity_unique_constraints():
    inspector = inspect(SessionLocal().bind)

    project_constraints = {
        constraint["name"]: tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints("projects")
    }
    contractor_constraints = {
        constraint["name"]: tuple(constraint["column_names"])
        for constraint in inspector.get_unique_constraints("contractors")
    }

    assert project_constraints["uq_projects_source_source_id"] == ("source", "source_id")
    assert contractor_constraints["uq_contractors_source_source_id"] == ("source", "source_id")


def test_phase21_projects_reject_duplicate_source_identity():
    session = SessionLocal()
    source_id = f"phase21-project-{uuid.uuid4()}"
    try:
        session.add(Project(name="Phase 21 duplicate test", source="phase21", source_id=source_id))
        session.flush()

        session.add(Project(name="Phase 21 duplicate test 2", source="phase21", source_id=source_id))
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()
    finally:
        session.close()


def test_phase21_contractors_reject_duplicate_source_identity():
    session = SessionLocal()
    source_id = f"phase21-contractor-{uuid.uuid4()}"
    try:
        session.add(Contractor(company_name="Phase 21 duplicate test", source="phase21", source_id=source_id))
        session.flush()

        session.add(Contractor(company_name="Phase 21 duplicate test 2", source="phase21", source_id=source_id))
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()
    finally:
        session.close()


def test_phase21_existing_pipeline_remains_idempotent():
    client = TestClient(app)
    first = client.post("/pipeline/local/run")
    second = client.post("/pipeline/local/run")

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["projects_discovered"] == 3
    assert second.json()["projects_discovered"] == 3
    assert first.json()["matches_generated"] == 7
    assert second.json()["matches_generated"] == 7
