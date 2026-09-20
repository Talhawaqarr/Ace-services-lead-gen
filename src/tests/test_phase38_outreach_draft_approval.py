from pathlib import Path


def test_outreach_approval_model_and_migration_exist():
    core = Path("src/models/core.py").read_text(encoding="utf-8")
    migration = Path("alembic/versions/0009_outreach_draft_audit.py").read_text(encoding="utf-8")
    assert "class OutreachDraftAudit" in core
    assert 'revision = "0009"' in migration
    assert 'down_revision = "0008"' in migration


def test_outreach_approval_service_has_controlled_transitions():
    service = Path("src/outreach/service.py").read_text(encoding="utf-8")
    assert 'VALID_DRAFT_STATUSES = {"DRAFT", "APPROVED", "REJECTED"}' in service
    assert 'VALID_DRAFT_TRANSITIONS' in service
    assert "OutreachDraftAudit" in service
    assert "set_outreach_draft_status" in service


def test_api_exposes_outreach_approval_and_audit_endpoints():
    api = Path("src/api.py").read_text(encoding="utf-8")
    assert '@app.post("/outreach-drafts/{draft_id}/status"' in api
    assert '@app.get("/outreach-drafts/{draft_id}/reviews"' in api
    assert "set_outreach_draft_status" in api
    assert "list_outreach_draft_audits" in api
