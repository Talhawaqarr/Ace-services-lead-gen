import os
from src.providers.mock.mock_bid import MockBidProvider
from src.providers.mock.mock_contractor import MockContractorProvider
from src.providers.mock.mock_email import MockEmailProvider


def test_mock_bid_returns_projects():
    p = MockBidProvider()
    res = p.list_projects()
    assert "projects" in res
    assert isinstance(res["projects"], list)


def test_mock_contractor_search():
    c = MockContractorProvider()
    res = c.search_companies("Acme")
    assert "companies" in res


def test_mock_email_stores():
    e = MockEmailProvider()
    payload = {"to": "test@example.com", "subject": "hi", "body": "hello"}
    r = e.send_email(payload)
    assert r["status"] == "stored"
    assert "local_id" in r
