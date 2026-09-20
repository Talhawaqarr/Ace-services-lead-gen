from pathlib import Path


def test_outreach_draft_model_and_migration_exist():
    core = Path("src/models/core.py").read_text(encoding="utf-8")
    migration = Path("alembic/versions/0008_outreach_drafts.py").read_text(encoding="utf-8")
    assert "class OutreachDraft" in core
    assert 'UniqueConstraint("match_id", "template_version"' in core
    assert 'revision = "0008"' in migration
    assert 'down_revision = "0007"' in migration


def test_outreach_service_requires_approval_and_is_deterministic():
    service = Path("src/outreach/service.py").read_text(encoding="utf-8")
    assert 'match.review_status != "APPROVED"' in service
    assert 'TEMPLATE_VERSION = "deterministic-v1"' in service
    assert "Contractor has no primary email" in service
    assert "If your team needs additional estimating capacity" in service
    assert 'OutreachDraft.match_id == match.id' in service


def test_api_exposes_outreach_draft_endpoints():
    api = Path("src/api.py").read_text(encoding="utf-8")
    assert '@app.post("/matches/{match_id}/outreach-draft"' in api
    assert '@app.get("/matches/{match_id}/outreach-draft"' in api
    assert "build_outreach_draft" in api
