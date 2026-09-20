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

    sam_projects = []
    offset = 0
    while True:
        projects = client.get(f"/projects?limit=100&offset={offset}")
        assert projects.status_code == 200, projects.text
        page = projects.json()
        sam_projects.extend(item for item in page if item["source"] == "samgov")
        if len(page) < 100:
            break
        offset += 100

    sam_projects_by_source_id = {item["source_id"]: item for item in sam_projects}
    assert {"SAM-1001", "SAM-1002", "SAM-1003", "SAM-1004"} <= set(sam_projects_by_source_id)

    project = sam_projects_by_source_id["SAM-1001"]
    matches = client.get(f"/projects/{project['id']}/matches")
    assert matches.status_code == 200, matches.text
    payload = matches.json()
    assert payload["project"]["id"] == project["id"]
    assert payload["summary"]["total"] == 8
    assert len(payload["matches"]) == 8
