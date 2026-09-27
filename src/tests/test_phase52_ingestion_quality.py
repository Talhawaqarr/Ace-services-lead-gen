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


def _samgov_record(**overrides):
    payload = {
        "source": "samgov",
        "solicitationNumber": "19SA4026C0008",
        "title": "AWARD NOTICE 19SA4026C0008 CONSTRUCTION OF SIDEWALKS",
        "naicsCode": "236220",
        "active": "Yes",
    }
    payload.update(overrides)
    return payload


def test_samgov_place_of_performance_objects_are_flattened_to_names():
    normalized, error = _project_record_for(
        _samgov_record(
            placeOfPerformance={
                "city": {"Code": "Jeddah", "Name": "Jeddah"},
                "state": {"Code": "CA", "Name": "California"},
                "country": {"Code": "SAU", "Name": "SAUDI ARABIA"},
            }
        )
    )

    assert error is None
    assert normalized["city"] == "Jeddah"
    assert normalized["state"] == "CA"
    assert "{" not in normalized["city"]


def test_samgov_place_of_performance_string_location_is_unchanged():
    normalized, error = _project_record_for(
        _samgov_record(placeOfPerformance={"city": "Oakland", "state": "CA"})
    )

    assert error is None
    assert normalized["city"] == "Oakland"
    assert normalized["state"] == "CA"


def test_samgov_place_of_performance_falls_back_to_code_when_name_missing():
    normalized, error = _project_record_for(
        _samgov_record(placeOfPerformance={"city": {"Code": "Jeddah"}, "state": {}})
    )

    assert error is None
    assert normalized["city"] == "Jeddah"
    assert normalized["state"] is None


def test_samgov_place_of_performance_null_and_missing_values_stay_empty():
    normalized, error = _project_record_for(
        _samgov_record(placeOfPerformance={"city": None, "state": {}})
    )

    assert error is None
    assert normalized["city"] is None
    assert normalized["state"] is None

    without_place, error = _project_record_for(_samgov_record())

    assert error is None
    assert without_place["city"] is None
    assert without_place["state"] is None


def test_samgov_top_level_state_object_is_flattened_and_long_names_trimmed():
    normalized, error = _project_record_for(
        _samgov_record(city={"Code": "Oakland", "Name": "Oakland"}, state={"Code": "CA", "Name": "California"})
    )

    assert error is None
    assert normalized["city"] == "Oakland"
    # Existing behaviour for a long state string is kept: take the first word
    # and keep the two-letter code, so a dict never leaks its repr.
    assert normalized["state"] == "CA"

    foreign, error = _project_record_for(
        _samgov_record(city={"Code": "Jeddah", "Name": "Jeddah"}, state={"Code": "02", "Name": "Makkah"})
    )

    assert error is None
    assert foreign["city"] == "Jeddah"
    assert foreign["state"].startswith("MA")
    assert "{" not in foreign["state"]
