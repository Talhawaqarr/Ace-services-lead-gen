from src.matching.engine import match_project, normalize_trade_name


def _project(**overrides):
    data = {
        "id": "proj-1",
        "name": "Downtown Library Renovation",
        "source": "synthetic",
        "source_id": "proj-1",
        "city": "Sacramento",
        "state": "CA",
        "latitude": 38.5816,
        "longitude": -121.4944,
        "trades": ["general"],
        "estimated_value": 1200000,
        "bid_date": "2026-12-01",
    }
    data.update(overrides)
    return data


def _contractor(**overrides):
    data = {
        "id": "cont-1",
        "company_name": "Acme Builders LLC",
        "normalized_name": "Acme Builders LLC",
        "source": "synthetic",
        "source_id": "cont-1",
        "city": "Sacramento",
        "state": "CA",
        "latitude": 38.5816,
        "longitude": -121.4944,
        "trades": ["general"],
    }
    data.update(overrides)
    return data


def test_normalize_trade_name():
    assert normalize_trade_name("electrical contractor") == "electrical"
    assert normalize_trade_name("Electrical Work") == "electrical"
    assert normalize_trade_name("General") == "general"


def test_match_project_returns_ranked_results():
    project = _project()
    contractors = [
        _contractor(id="cont-1", company_name="Acme Builders LLC", trades=["general"], city="Sacramento", state="CA", latitude=38.5816, longitude=-121.4944),
        _contractor(id="cont-2", company_name="Civil Works Co", trades=["civil"], city="Houston", state="TX", latitude=29.7604, longitude=-95.3698),
        _contractor(id="cont-3", company_name="General Builders", trades=["general"], city="San Jose", state="CA", latitude=37.3382, longitude=-121.8863),
    ]

    results = match_project(project, contractors)
    assert len(results) == 3
    assert results[0]["project_id"] == project["id"]
    assert results[0]["contractor_id"] == "cont-1"
    assert results[0]["ranking"] == 1
    assert results[0]["confidence"] in {"HIGH", "MEDIUM", "LOW"}
    assert results[0]["matcher_version"] == "deterministic-v1"
    assert results[0]["match_score"] >= results[1]["match_score"] >= results[2]["match_score"]
    assert 0.0 <= results[0]["match_score"] <= 1.0
    assert "Trade overlap" in results[0]["positive_factors"][0]


def test_trade_mismatch_is_lower_score_and_repeatable():
    project = _project(trades=["electrical"])
    contractor = _contractor(id="cont-bad", company_name="Civil Works Co", trades=["civil"], city="Oakland", state="CA", latitude=37.8044, longitude=-122.2711)

    first = match_project(project, [contractor])
    second = match_project(project, [contractor])
    assert first == second
    assert first[0]["match_score"] < 0.7
    assert first[0]["negative_factors"]


def test_missing_trade_data_is_unknown_not_mismatch():
    project = _project(trades=[])
    contractor = _contractor(id="cont-missing", company_name="Regional Builders", trades=[], city="Sacramento", state="CA", latitude=38.5816, longitude=-121.4944)

    result = match_project(project, [contractor])[0]
    assert result["unknown_factors"]
    assert result["negative_factors"] == []
    assert result["match_score"] >= 0.0


def test_missing_city_is_neutral_when_state_matches():
    project = _project(city="Sacramento", state="CA")
    contractor = _contractor(id="cont-no-city", city=None, state="CA", latitude=38.5816, longitude=-121.4944)

    result = match_project(project, [contractor])[0]
    assert result["components"]["geography"]["score"] == 12.0
    assert result["match_score"] > 0.0


def test_unsupported_fields_are_ignored_by_current_engine():
    project = _project()
    contractor = _contractor(id="cont-inactive", company_name="Inactive Builder", trades=["general"], city="Sacramento", state="CA", latitude=38.5816, longitude=-121.4944, is_active=False, project_status="inactive")

    result = match_project(project, [contractor])[0]
    assert result["match_score"] == match_project(project, [_contractor(id="cont-active", company_name="Active Builder", trades=["general"], city="Sacramento", state="CA", latitude=38.5816, longitude=-121.4944)])[0]["match_score"]


def test_equal_scores_are_sorted_stably_by_name():
    project = _project()
    alpha = _contractor(id="cont-alpha", company_name="Alpha Builders", trades=["general"], city="Sacramento", state="CA", latitude=38.5816, longitude=-121.4944)
    zeta = _contractor(id="cont-zeta", company_name="Zeta Builders", trades=["general"], city="Sacramento", state="CA", latitude=38.5816, longitude=-121.4944)

    results = match_project(project, [zeta, alpha])
    assert [r["contractor_id"] for r in results] == ["cont-alpha", "cont-zeta"]


def test_bid_timing_is_supported_and_normalized():
    project = _project(bid_date="2026-12-01")
    contractor = _contractor(id="cont-timing", company_name="Timing Builders", trades=["general"], city="Sacramento", state="CA", latitude=38.5816, longitude=-121.4944)

    result = match_project(project, [contractor])[0]
    assert result["components"]["bid_timing"]["score"] == 5.0
    assert result["match_score"] > 0.0


def test_match_score_is_normalized_to_0_1_and_confidence_is_deterministic():
    project = _project()
    contractor = _contractor(id="cont-confidence", company_name="Confidence Builders", trades=["general"], city="Sacramento", state="CA", latitude=38.5816, longitude=-121.4944)

    result = match_project(project, [contractor])[0]
    assert 0.0 <= result["match_score"] <= 1.0
    assert result["confidence"] in {"LOW", "MEDIUM", "HIGH"}
    assert result["match_score"] == round(result["raw_score"] / result["max_available_score"], 4)
