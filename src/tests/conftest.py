import pytest
from sqlalchemy.orm import close_all_sessions


@pytest.fixture(autouse=True)
def close_database_sessions():
    yield
    close_all_sessions()
