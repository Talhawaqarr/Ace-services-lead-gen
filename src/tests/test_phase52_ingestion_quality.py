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


def test_samgov_top_level_state_object_prefers_a_real_two_letter_code():
    normalized, error = _project_record_for(
        _samgov_record(city={"Code": "Oakland", "Name": "Oakland"}, state={"Code": "CA", "Name": "California"})
    )

    assert error is None
    assert normalized["city"] == "Oakland"
    # A nested state object is read object-aware: the real two-letter code wins,
    # so a dict never leaks its repr into the canonical record.
    assert normalized["state"] == "CA"
    assert "{" not in normalized["state"]

    foreign, error = _project_record_for(
        _samgov_record(city={"Code": "Jeddah", "Name": "Jeddah"}, state={"Code": "02", "Name": "Makkah"})
    )

    assert error is None
    assert foreign["city"] == "Jeddah"
    # "02" is a region number and "Makkah" is a province name, so no US state is
    # fabricated by truncating them into "02"/"MA".
    assert foreign["state"] is None


# --- Live SAM.gov v2 nested location objects, as observed in the raw payload ---


NESTED_SAM_PLACE = {
    "city": {"code": "Jeddah", "name": "Jeddah"},
    "state": {"code": "CR-H", "name": "Heredia"},
    "country": {"code": "CRI", "name": "Costa Rica"},
}


def test_nested_city_object_becomes_a_plain_city_string():
    normalized, error = _project_record_for(_samgov_record(placeOfPerformance=dict(NESTED_SAM_PLACE)))

    assert error is None
    assert normalized["city"] == "Jeddah"
    assert isinstance(normalized["city"], str)


def test_nested_state_object_does_not_fabricate_a_us_state_code():
    normalized, error = _project_record_for(_samgov_record(placeOfPerformance=dict(NESTED_SAM_PLACE)))

    assert error is None
    # "CR-H" is an ISO subdivision and "Heredia" is a province name, so neither
    # is a two-letter US state code and no state is persisted.
    assert normalized["state"] is None

    domestic, error = _project_record_for(
        _samgov_record(
            placeOfPerformance={
                "city": {"code": "Oakland", "name": "Oakland"},
                "state": {"code": "CA", "name": "California"},
            }
        )
    )

    assert error is None
    assert domestic["state"] == "CA"


def test_nested_country_object_is_readable_from_provenance():
    normalized, error = _project_record_for(_samgov_record(placeOfPerformance=dict(NESTED_SAM_PLACE)))

    assert error is None
    assert normalized["provenance"]["place_of_performance_country"] == "Costa Rica"


def test_list_of_place_objects_is_normalized_instead_of_crashing():
    normalized, error = _project_record_for(_samgov_record(placeOfPerformance=[dict(NESTED_SAM_PLACE)]))

    assert error is None
    assert normalized["city"] == "Jeddah"
    assert normalized["state"] is None
    assert normalized["provenance"]["place_of_performance_country"] == "Costa Rica"


def test_no_python_dict_or_list_representation_is_persisted():
    places = [
        dict(NESTED_SAM_PLACE),
        dict(NESTED_SAM_PLACE, city=[{"code": "Jeddah", "name": "Jeddah"}]),
        dict(NESTED_SAM_PLACE, state=[{"code": "CR-H", "name": "Heredia"}]),
        {"city": {}, "state": {}, "country": {}},
        [dict(NESTED_SAM_PLACE)],
    ]

    for place in places:
        normalized, error = _project_record_for(_samgov_record(placeOfPerformance=place))
        assert error is None, place
        for field in ("city", "state"):
            value = normalized[field]
            assert value is None or "{" not in value, (field, value)


def test_plain_string_locations_are_unchanged():
    normalized, error = _project_record_for(
        _samgov_record(placeOfPerformance={"city": "Oakland", "state": "CA", "country": "USA"})
    )

    assert error is None
    assert normalized["city"] == "Oakland"
    assert normalized["state"] == "CA"
    assert normalized["provenance"]["place_of_performance_country"] == "USA"


def test_null_and_missing_location_shapes_do_not_crash():
    for place in (None, [], {}, "not-a-mapping", {"city": None, "state": None}):
        normalized, error = _project_record_for(_samgov_record(placeOfPerformance=place))
        assert error is None, place
        assert normalized["city"] is None, place
        assert normalized["state"] is None, place

    without_place, error = _project_record_for(_samgov_record())
    assert error is None
    assert without_place["city"] is None
    assert without_place["state"] is None
