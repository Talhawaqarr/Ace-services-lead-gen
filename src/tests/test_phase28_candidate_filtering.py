from __future__ import annotations

from src.db import SessionLocal
from src.models.core import Contractor, Project
from src.pipeline.service import discover_contractors


def test_contractor_discovery_uses_state_and_trade_as_candidate_filters():
    session = SessionLocal()
    try:
        project = Project(
            name="Phase 28 Project",
            source="phase28-test",
            source_id="P28",
            state="CA",
            trades=["general"],
        )
        session.add(project)
        session.flush()

        session.add_all([
            Contractor(company_name="Same State Same Trade", normalized_name="same state same trade", source="phase28-test", source_id="C1", state="CA", trades=["general"]),
            Contractor(company_name="Same State Wrong Trade", normalized_name="same state wrong trade", source="phase28-test", source_id="C2", state="CA", trades=["electrical"]),
            Contractor(company_name="Wrong State Same Trade", normalized_name="wrong state same trade", source="phase28-test", source_id="C3", state="WA", trades=["general"]),
            Contractor(company_name="Unknown Trade", normalized_name="unknown trade", source="phase28-test", source_id="C4", state="CA", trades=[]),
        ])
        session.flush()

        candidates = discover_contractors(session, project, source="phase28-test")
        assert [item["source_id"] for item in candidates] == ["C1", "C4"]
    finally:
        session.rollback()
        session.close()
