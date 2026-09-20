from __future__ import annotations

from src.ingestion.service import _project_record_for
from src.opportunity.service import qualifies_opportunity


def test_samgov_active_field_normalizes_to_active_status():
    normalized, error = _project_record_for(
        {
            "source": "samgov",
            "solicitationNumber": "S-1",
            "title": "Construction project",
            "active": "Yes",
            "naicsCode": "236220",
            "postedDate": "2026-09-19T12:00:00Z",
            "reponseDeadLine": "2026-10-19T12:00:00Z",
        }
    )

    assert error is None
    assert normalized["status"] == "ACTIVE"


def test_samgov_inactive_field_normalizes_to_inactive_status():
    normalized, error = _project_record_for(
        {
            "source": "samgov",
            "solicitationNumber": "S-2",
            "title": "Construction project",
            "active": "No",
            "naicsCode": "236220",
            "postedDate": "2026-09-19T12:00:00Z",
            "reponseDeadLine": "2026-10-19T12:00:00Z",
        }
    )

    assert error is None
    assert normalized["status"] == "INACTIVE"


def test_active_samgov_construction_opportunity_qualifies():
    normalized, error = _project_record_for(
        {
            "source": "samgov",
            "solicitationNumber": "S-3",
            "title": "Construction project",
            "active": "Yes",
            "naicsCode": "236220",
            "postedDate": "2026-09-19T12:00:00Z",
            "reponseDeadLine": "2026-10-19T12:00:00Z",
        }
    )

    assert error is None

    from src.models.core import Project

    project = Project(**{
        key: normalized[key]
        for key in (
            "name",
            "source",
            "source_id",
            "city",
            "state",
            "trades",
            "bid_date",
            "posted_date",
            "response_deadline",
            "status",
            "description",
            "source_url",
            "estimated_value",
            "provenance",
        )
    })

    assert qualifies_opportunity(project) is True
