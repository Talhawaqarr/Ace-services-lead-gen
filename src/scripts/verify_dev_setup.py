import os
import sys
from pathlib import Path
from sqlalchemy import text
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.db import engine

load_dotenv()


def check_db():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            return True
    except Exception as e:
        print("DB connection failed:", e)
        return False


def check_migrations():
    try:
        with engine.connect() as conn:
            val = conn.execute(text("SELECT to_regclass('public.alembic_version')")).scalar()
            return val is not None
    except Exception as e:
        print("Migration check failed:", e)
        return False


def check_schema():
    try:
        with engine.connect() as conn:
            tables = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")).scalars().all()
            required = {"projects", "contractors", "alembic_version"}
            return required.issubset(set(tables))
    except Exception as e:
        print("Schema check failed:", e)
        return False


def check_synthetic_loaded():
    try:
        with engine.connect() as conn:
            project_count = conn.execute(text("SELECT count(*) FROM projects")).scalar()
            contractor_count = conn.execute(text("SELECT count(*) FROM contractors")).scalar()
            print("projects in DB:", project_count)
            print("contractors in DB:", contractor_count)
            return project_count > 0 and contractor_count > 0
    except Exception as e:
        print("Error checking synthetic tables:", e)
        return False


def check_mock_config():
    return os.environ.get("EMAIL_PROVIDER", "mock").lower() == "mock" and os.environ.get("LLM_PROVIDER", "mock").lower() == "mock"


def check_dry_run():
    return os.environ.get("DRY_RUN", "true").lower() in ("1", "true", "yes")


def check_no_required_api_keys():
    return not any([
        os.environ.get("MAPBOX_TOKEN"),
        os.environ.get("OPENAI_API_KEY"),
        os.environ.get("SENDGRID_API_KEY"),
        os.environ.get("MAILGUN_API_KEY"),
        os.environ.get("POSTMARK_API_KEY"),
    ])


def main():
    print("DB connected:", check_db())
    print("Migrations present (alembic_version table):", check_migrations())
    print("Schema includes required tables:", check_schema())
    print("Synthetic data loaded:", check_synthetic_loaded())
    print("Mock providers configured:", check_mock_config())
    print("DRY_RUN enabled:", check_dry_run())
    print("No required API keys:", check_no_required_api_keys())


if __name__ == '__main__':
    main()
