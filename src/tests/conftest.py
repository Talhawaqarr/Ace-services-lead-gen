import pytest

import src.db as db


@pytest.fixture(autouse=True)
def close_database_sessions(monkeypatch):
    created_sessions = []

    original_session_local = db.SessionLocal

    def tracked_session(*args, **kwargs):
        session = original_session_local(*args, **kwargs)
        created_sessions.append(session)
        return session

    monkeypatch.setattr(db, "SessionLocal", tracked_session)

    yield

    for session in created_sessions:
        try:
            session.rollback()
        finally:
            session.close()
