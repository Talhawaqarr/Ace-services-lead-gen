from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_dockerfile_runs_as_non_root_and_has_healthcheck():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "USER app" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "alembic upgrade head" in dockerfile or "alembic upgrade head" in (ROOT / "scripts" / "start.sh").read_text(encoding="utf-8")


def test_compose_is_explicitly_zero_cost_development_runtime():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "postgres:16-alpine" in compose
    assert "APP_ENV: development" in compose
    assert "INGESTION_MODE: fixture" in compose
    assert "EMAIL_PROVIDER: mock" in compose
    assert 'DRY_RUN: "true"' in compose


def test_start_script_waits_for_database_before_migrations():
    script = (ROOT / "scripts" / "start.sh").read_text(encoding="utf-8")
    assert "psycopg2.connect" in script
    assert "alembic upgrade head" in script
    assert "exec uvicorn src.api:app" in script


def test_deployment_docs_mark_compose_as_development_only():
    docs = (ROOT / "docs" / "PHASE18_DEPLOYMENT.md").read_text(encoding="utf-8")
    assert "development-only" in docs
    assert "not a production deployment template" in docs
