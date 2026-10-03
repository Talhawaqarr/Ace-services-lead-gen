from __future__ import annotations

from datetime import datetime, timezone

from src.ingestion.service import _project_record_for
from src.opportunity.service import qualifies_opportunity
from src.models.core import Project


def _project(**overrides):
    values = {"name": "Phase 25 Opportunity", "source": "samgov", "source_id": "P25-1", "status": "ACTIVE", "response_deadline": "2026-10-10T17:00:00Z", "provenance": {"construction_relevance": "likely"}}
    values.update(overrides)
    return Project(**values)


_QUALIFICATION_PROVENANCE_KEYS = (
    "procurement_type",
    "naics_code",
    "classification_code",
    "place_of_performance_country",
)


def _solicitation(**overrides):
    """A US construction solicitation in the project's normalized field shape.

    Keys listed in ``_QUALIFICATION_PROVENANCE_KEYS`` are written into provenance;
    anything else is a canonical Project field such as ``name`` or ``status``.
    """
    provenance = {
        "construction_relevance": "likely",
        "procurement_type": "Solicitation",
        "naics_code": "236220",
        "classification_code": "M",
        "place_of_performance_country": "USA",
    }
    fields = {}
    for key, value in overrides.items():
        if key in _QUALIFICATION_PROVENANCE_KEYS:
            provenance[key] = value
        else:
            fields[key] = value
    return _project(provenance=provenance, **fields)


def test_qualifies_active_construction_opportunity():
    project = _project()
    now = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
    assert qualifies_opportunity(project, now=now)


def test_rejects_inactive_opportunity():
    assert not qualifies_opportunity(_project(status="INACTIVE"))


def test_rejects_non_construction_opportunity():
    assert not qualifies_opportunity(_project(provenance={"construction_relevance": "unlikely"}))


def test_deadline_window_is_deterministic():
    project = _project()
    now = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
    assert qualifies_opportunity(project, now=now, deadline_within_days=21)
    assert not qualifies_opportunity(project, now=now, deadline_within_days=10)


def test_missing_deadline_is_rejected_when_window_requested():
    project = _project(response_deadline=None)
    now = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
    assert not qualifies_opportunity(project, now=now, deadline_within_days=30)


# --- Notice type, construction NAICS, and place of performance boundaries ---


def test_us_combined_synopsis_solicitation_with_construction_naics_qualifies():
    assert qualifies_opportunity(_solicitation(procurement_type="Combined Synopsis/Solicitation"))


def test_us_solicitation_with_construction_naics_qualifies():
    assert qualifies_opportunity(_solicitation())


def test_special_notice_and_industry_day_are_rejected():
    for notice in ("Special Notice", "Industry Day", "Reverse Industry Day"):
        assert not qualifies_opportunity(_solicitation(procurement_type=notice)), notice


def test_sources_sought_and_request_for_information_are_rejected():
    for notice in ("Sources Sought", "Request for Information", "Request for Information (RFI)"):
        assert not qualifies_opportunity(_solicitation(procurement_type=notice)), notice


def test_notice_type_decides_not_the_title_wording():
    looks_like_a_solicitation = _solicitation(name="Solicitation for Construction Services")
    assert qualifies_opportunity(looks_like_a_solicitation)

    actually_an_event = _solicitation(
        name="Construction Solicitation Briefing for the Road Program",
        procurement_type="Industry Day",
    )
    assert not qualifies_opportunity(actually_an_event)


def test_construction_only_requires_a_construction_family_naics_code():
    assert qualifies_opportunity(_solicitation(naics_code="237310"))
    assert not qualifies_opportunity(_solicitation(naics_code="541512"))
    assert not qualifies_opportunity(_solicitation(naics_code="221310"))


def test_construction_naics_is_ignored_when_construction_only_is_disabled():
    assert qualifies_opportunity(_solicitation(naics_code="541512"), construction_only=False)


def test_costa_rica_construction_solicitation_is_rejected():
    assert not qualifies_opportunity(_solicitation(place_of_performance_country="CRI"))


def test_south_korea_construction_solicitation_is_rejected():
    assert not qualifies_opportunity(_solicitation(place_of_performance_country="KOR"))


def test_saudi_arabia_construction_solicitation_is_rejected():
    assert not qualifies_opportunity(_solicitation(place_of_performance_country="SAU"))


def test_equivalent_us_country_representations_are_accepted():
    for country in ("USA", "usa", "U.S.A.", "United States", "United States of America"):
        assert qualifies_opportunity(_solicitation(place_of_performance_country=country)), country


def test_active_and_deadline_behavior_still_applies_to_a_full_solicitation():
    project = _solicitation()
    now = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)

    assert not qualifies_opportunity(_solicitation(status="INACTIVE"), now=now)
    assert qualifies_opportunity(project, now=now, deadline_within_days=21)
    assert not qualifies_opportunity(project, now=now, deadline_within_days=10)


# --- The rules read the fields ingestion already normalizes ---


_PROJECT_FIELDS = (
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


def _samgov_record(**overrides):
    payload = {
        "source": "samgov",
        "solicitationNumber": "W912-26-R-0001",
        "title": "Construction of Sidewalks and Curb Repair",
        "naicsCode": "236220",
        "classificationCode": "M",
        "type": "Solicitation",
        "active": "Yes",
        "postedDate": "2026-09-19T12:00:00Z",
        "reponseDeadLine": "2026-10-19T12:00:00Z",
        "organizationName": "U.S. Army Corps of Engineers",
        "placeOfPerformance": {"city": "Oakland", "state": "CA", "country": "USA"},
    }
    payload.update(overrides)
    return payload


def _ingested(raw):
    normalized, error = _project_record_for(raw)
    assert error is None, error
    return Project(**{key: normalized[key] for key in _PROJECT_FIELDS})


def test_ingestion_persists_the_notice_type_naics_and_performance_country():
    normalized, error = _project_record_for(_samgov_record())

    assert error is None
    assert normalized["provenance"]["procurement_type"] == "Solicitation"
    assert normalized["provenance"]["naics_code"] == "236220"
    assert normalized["provenance"]["place_of_performance_country"] == "USA"


def test_ingested_us_construction_solicitation_qualifies():
    assert qualifies_opportunity(_ingested(_samgov_record())) is True


def test_ingested_industry_day_event_never_qualifies():
    project = _ingested(
        _samgov_record(
            solicitationNumber="W912-26-R-0002",
            title="REVERSE INDUSTRY DAY FOR THE CONSTRUCTION PROGRAM",
            type="Industry Day",
            baseType="Industry Day",
        )
    )

    assert qualifies_opportunity(project) is False


def test_ingested_foreign_place_of_performance_is_rejected_despite_a_us_contracting_office():
    project = _ingested(
        _samgov_record(
            solicitationNumber="W912-26-R-0003",
            placeOfPerformance={
                "city": "San Jose",
                "state": {"Code": "01", "Name": "SAN JOSE"},
                "country": {"Code": "CRI", "Name": "COSTA RICA"},
            },
        )
    )

    assert project.provenance["organization_name"] == "U.S. Army Corps of Engineers"
    assert project.provenance["place_of_performance_country"] == "COSTA RICA"
    assert qualifies_opportunity(project) is False

