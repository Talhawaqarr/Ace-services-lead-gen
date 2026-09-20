from src.ingestion.service import _contractor_record_for


def test_contractor_contact_fields_are_normalized():
    normalized, error = _contractor_record_for({
        "source": "samgov",
        "source_id": "CONTACT-1",
        "company_name": "Example Builder",
        "state": " tx ",
        "contact": {"email": " SALES@EXAMPLE.COM ", "phone": " +1 555 0102 "},
        "website": " https://example.com ",
    })
    assert error is None
    assert normalized["primary_email"] == "sales@example.com"
    assert normalized["primary_phone"] == "+1 555 0102"
    assert normalized["website"] == "https://example.com"


def test_missing_contact_fields_are_allowed():
    normalized, error = _contractor_record_for({
        "source": "samgov", "source_id": "CONTACT-2", "company_name": "No Contact Builder"
    })
    assert error is None
    assert normalized["primary_email"] is None
    assert normalized["primary_phone"] is None
    assert normalized["website"] is None
