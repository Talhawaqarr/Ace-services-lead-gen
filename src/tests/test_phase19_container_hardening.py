from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_dockerignore_excludes_secrets_and_local_dev_artifacts():
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert ".git" in dockerignore
    assert ".venv" in dockerignore
    assert ".env" in dockerignore
    assert "!.env.example" in dockerignore
    assert "__pycache__" in dockerignore


def test_dockerfile_uses_script_shebang_directly():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert 'ENTRYPOINT ["./scripts/start.sh"]' in dockerfile
    assert 'ENTRYPOINT ["sh", "./scripts/start.sh"]' not in dockerfile


def test_compose_keeps_database_internal_to_compose_network():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    db_section = compose.split("  api:", 1)[0]
    assert 'ports:' not in db_section
    assert '5432:5432' not in db_section
    assert '5433:5432' not in db_section
