from __future__ import annotations

from src.db import SessionLocal
from src.ingestion.service import ingest_source_records
from src.models.core import Project
from src.providers.samgov import SAMGovProvider


def test_samgov_project_trade_signals_are_derived_from_naics():
    session = SessionLocal()
    try:
        ingest_source_records(session, SAMGovProvider(), source_name="samgov")

        fire_station = session.query(Project).filter(Project.source_id == "SAM-1001").one()
        water = session.query(Project).filter(Project.source_id == "SAM-1003").one()
        road = session.query(Project).filter(Project.source_id == "SAM-1004").one()

        assert fire_station.trades == ["general"]
        assert water.trades == ["civil"]
        assert road.trades == ["civil"]
    finally:
        session.rollback()
        session.close()
