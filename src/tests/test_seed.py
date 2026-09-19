import os
from dotenv import load_dotenv
from src.scripts.load_synthetic_data import main as load_main
from src.db import engine
from sqlalchemy import text


def test_seed_idempotent(tmp_path, monkeypatch):
    load_dotenv()
    # Run seed twice and ensure no exception and counts stable
    load_main()
    with engine.connect() as conn:
        c1 = conn.execute(text("SELECT count(*) FROM projects")).scalar()
    load_main()
    with engine.connect() as conn:
        c2 = conn.execute(text("SELECT count(*) FROM projects")).scalar()
    assert c1 == c2
