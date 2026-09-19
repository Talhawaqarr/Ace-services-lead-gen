import uuid

from fastapi.testclient import TestClient

from src.api import app
from src.db import get_session
from src.models.core import Contractor, Project
from src.review.service import generate_matches

client = TestClient(app)


def _project_with_uuid(**overrides):
    project_id = str(uuid.uuid4())
    payload = {
        "id": project_id,
        "name": "Phase 4 Project",
        "source": "synthetic",
        "source_id": f"phase4-{project_id}",
        "city": "Sacramento",
        "state": "CA",
        "latitude": 38.5816,
        "longitude": -121.4944,
        "trades": ["general"],
        "bid_date": "2026-12-01",
        "estimated_value": 1000000,
    }
    payload.update(overrides)
    return payload


def _contractor_with_uuid(**overrides):
    contractor_id = str(uuid.uuid4())
    payload = {
        "id": contractor_id,
        "company_name": "Phase 4 Contractor",
        "normalized_name": "Phase 4 Contractor",
        "source": "synthetic",
        "source_id": f"phase4-c-{contractor_id}",
        "city": "Sacramento",
        "state": "CA",
        "latitude": 38.5816,
        "longitude": -121.4944,
        "trades": ["general"],
    }
    payload.update(overrides)
    return payload


def test_projects_list_and_detail_work():
    project = _project_with_uuid()
    session = get_session()
    session.add(Project(
        id=uuid.UUID(project["id"]),
        name=project["name"],
        source=project["source"],
        source_id=project["source_id"],
        city=project["city"],
        state=project["state"],
        latitude=project["latitude"],
        longitude=project["longitude"],
        trades=project["trades"],
        bid_date=project["bid_date"],
        estimated_value=project["estimated_value"],
        provenance={"source": "synthetic"},
    ))
    session.commit()

    list_response = client.get("/projects")
    assert list_response.status_code == 200
    ids = [item["id"] for item in list_response.json()]
    assert project["id"] in ids

    detail_response = client.get(f"/projects/{project['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["name"] == project["name"]


def test_project_matches_and_detail_endpoints_work():
    project = _project_with_uuid()
    contractor = _contractor_with_uuid(company_name="Alpha Match Builders", trades=["general"])
    contractor_b = _contractor_with_uuid(company_name="Beta Match Builders", trades=["electrical"], city="Denver", state="CO")

    session = get_session()
    session.add(Project(
        id=uuid.UUID(project["id"]),
        name=project["name"],
        source=project["source"],
        source_id=project["source_id"],
        city=project["city"],
        state=project["state"],
        latitude=project["latitude"],
        longitude=project["longitude"],
        trades=project["trades"],
        bid_date=project["bid_date"],
        estimated_value=project["estimated_value"],
        provenance={"source": "synthetic"},
    ))
    session.add(Contractor(
        id=uuid.UUID(contractor["id"]),
        company_name=contractor["company_name"],
        normalized_name=contractor["normalized_name"],
        source=contractor["source"],
        source_id=contractor["source_id"],
        city=contractor["city"],
        state=contractor["state"],
        trades=contractor["trades"],
        provenance={"source": "synthetic"},
    ))
    session.add(Contractor(
        id=uuid.UUID(contractor_b["id"]),
        company_name=contractor_b["company_name"],
        normalized_name=contractor_b["normalized_name"],
        source=contractor_b["source"],
        source_id=contractor_b["source_id"],
        city=contractor_b["city"],
        state=contractor_b["state"],
        trades=contractor_b["trades"],
        provenance={"source": "synthetic"},
    ))
    session.commit()

    generate_matches(session, project, [contractor, contractor_b])
    session.commit()

    matches_response = client.get(f"/projects/{project['id']}/matches")
    assert matches_response.status_code == 200, matches_response.text
    payload = matches_response.json()
    assert payload["project"]["id"] == project["id"]
    assert len(payload["matches"]) == 2
    assert payload["matches"][0]["ranking"] <= payload["matches"][1]["ranking"]

    match_detail = client.get(f"/matches/{payload['matches'][0]['id']}")
    assert match_detail.status_code == 200, match_detail.text
    assert match_detail.json()["match"]["project_id"] == project["id"]
    assert "evidence" in match_detail.json()


def test_review_endpoints_update_status_and_audit():
    project = _project_with_uuid()
    contractor = _contractor_with_uuid(company_name="Review Contractor", trades=["general"])

    session = get_session()
    session.add(Project(
        id=uuid.UUID(project["id"]),
        name=project["name"],
        source=project["source"],
        source_id=project["source_id"],
        city=project["city"],
        state=project["state"],
        latitude=project["latitude"],
        longitude=project["longitude"],
        trades=project["trades"],
        bid_date=project["bid_date"],
        estimated_value=project["estimated_value"],
        provenance={"source": "synthetic"},
    ))
    session.add(Contractor(
        id=uuid.UUID(contractor["id"]),
        company_name=contractor["company_name"],
        normalized_name=contractor["normalized_name"],
        source=contractor["source"],
        source_id=contractor["source_id"],
        city=contractor["city"],
        state=contractor["state"],
        trades=contractor["trades"],
        provenance={"source": "synthetic"},
    ))
    session.commit()

    match = generate_matches(session, project, [contractor])[0]
    session.commit()

    approve = client.post(f"/matches/{match.id}/review", json={"status": "APPROVED"})
    assert approve.status_code == 200, approve.text
    assert approve.json()["status"] == "APPROVED"

    reject = client.post(f"/matches/{match.id}/review", json={"status": "REJECTED"})
    assert reject.status_code == 200, reject.text
    assert reject.json()["status"] == "REJECTED"

    invalid = client.post(f"/matches/{match.id}/review", json={"status": "NOT_A_STATE"})
    assert invalid.status_code == 400


def test_missing_project_and_missing_match_are_404():
    missing_project = client.get("/projects/00000000-0000-0000-0000-000000000000")
    assert missing_project.status_code == 404

    missing_match = client.get("/matches/00000000-0000-0000-0000-000000000000")
    assert missing_match.status_code == 404
