from fastapi.testclient import TestClient

from src.api import app

client = TestClient(app)


def test_local_pipeline_persists_matches_and_is_idempotent():
    first = client.post("/pipeline/local/run")
    assert first.status_code == 200, first.text
    first_payload = first.json()

    second = client.post("/pipeline/local/run")
    assert second.status_code == 200, second.text
    second_payload = second.json()

    assert first_payload["projects_discovered"] == 4
    assert first_payload["projects_processed"] == 4
    assert first_payload["matches_generated"] == 32

    assert second_payload["projects_discovered"] == first_payload["projects_discovered"]
    assert second_payload["projects_processed"] == first_payload["projects_processed"]
    assert second_payload["matches_generated"] == first_payload["matches_generated"]

    projects = client.get("/projects?limit=100")
    assert projects.status_code == 200, projects.text
    sam_projects = [item for item in projects.json() if item["source"] == "samgov"]
    assert len(sam_projects) >= 4

    project = sam_projects[0]
    matches = client.get(f"/projects/{project['id']}/matches")
    assert matches.status_code == 200, matches.text
    payload = matches.json()
    assert payload["project"]["id"] == project["id"]
    assert payload["summary"]["total"] == 8
    assert len(payload["matches"]) == 8
