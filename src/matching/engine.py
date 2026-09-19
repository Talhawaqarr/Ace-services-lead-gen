from __future__ import annotations

from typing import Any, Iterable
import math
import re


MATCHER_VERSION = "deterministic-v1"
SUPPORTED_FEATURES = ("trade_overlap", "geography", "bid_timing")


def normalize_trade_name(value: str | None) -> str:
    if value is None:
        return ""
    cleaned = re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()
    if not cleaned:
        return ""
    cleaned = re.sub(r"\b(roofing|roofer)\b", "roofing", cleaned)
    cleaned = re.sub(r"\b(general contractor|general construction|general work|general)\b", "general", cleaned)
    cleaned = re.sub(r"\b(electrical contractor|electrical work|electrician|electrical)\b", "electrical", cleaned)
    cleaned = re.sub(r"\b(civil contractor|civil work|civil engineering|civil)\b", "civil", cleaned)
    cleaned = re.sub(r"\b(plumbing contractor|plumbing work|plumbing)\b", "plumbing", cleaned)
    cleaned = re.sub(r"\b(concrete contractor|concrete work|concrete)\b", "concrete", cleaned)
    cleaned = re.sub(r"\b(landscaping|landscape)\b", "landscaping", cleaned)
    cleaned = re.sub(r"\b(education|school)\b", "education", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _as_trade_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        normalized = normalize_trade_name(value)
        return [normalized] if normalized else []
    if isinstance(value, (list, tuple, set)):
        items: list[str] = []
        for item in value:
            normalized = normalize_trade_name(item)
            if normalized:
                items.append(normalized)
        return items
    return []


def _normalize_location(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _distance_km(lat1: float | None, lon1: float | None, lat2: float | None, lon2: float | None) -> float:
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return float("inf")
    radius_km = 6371.0
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_km * c


def _project_trade_set(project: dict[str, Any]) -> set[str]:
    trades = set()
    for raw in _as_trade_list(project.get("trades") or project.get("trade") or project.get("project_trade")):
        trades.add(raw)
    return trades


def _contractor_trade_set(contractor: dict[str, Any]) -> set[str]:
    trades = set()
    for raw in _as_trade_list(contractor.get("trades") or contractor.get("trade") or contractor.get("specialties")):
        trades.add(raw)
    return trades


def _score_trade_overlap(project: dict[str, Any], contractor: dict[str, Any]) -> tuple[float, list[str], list[str], list[str], float]:
    project_trades = _project_trade_set(project)
    contractor_trades = _contractor_trade_set(contractor)

    if not project_trades and not contractor_trades:
        return 0.0, [], [], ["Trade information unavailable"], 0.0
    if not project_trades:
        return 0.0, [], [], ["Project trade information unavailable"], 0.0
    if not contractor_trades:
        return 0.0, [], [], ["Contractor trade information unavailable"], 0.0

    overlap = project_trades & contractor_trades
    if overlap:
        score = 35.0 * (len(overlap) / max(len(project_trades), 1))
        return round(score, 2), [f"Trade overlap: {sorted(overlap)[0]}"], [], [], 35.0

    return 0.0, [], [f"Trade mismatch: project={sorted(project_trades)[:3]}, contractor={sorted(contractor_trades)[:3]}"], [], 35.0


def _score_geography(project: dict[str, Any], contractor: dict[str, Any]) -> tuple[float, list[str], list[str], list[str], float]:
    project_city = _normalize_location(project.get("city"))
    project_state = _normalize_location(project.get("state"))
    contractor_city = _normalize_location(contractor.get("city"))
    contractor_state = _normalize_location(contractor.get("state"))

    if project_state and contractor_state and project_state != contractor_state:
        return 0.0, [], [f"State mismatch: {project_state.upper()} vs {contractor_state.upper()}"], [], 18.0

    if project_city and contractor_city and project_state and contractor_state:
        if project_city == contractor_city and project_state == contractor_state:
            return 18.0, [f"Same city: {project_city.title()}"], [], [], 18.0
        if project_state == contractor_state:
            return 12.0, [f"Same state: {project_state.upper()}"], [], [], 12.0

    if project_state and contractor_state and project_state == contractor_state:
        return 12.0, [f"Same state: {project_state.upper()}"], [], [], 12.0

    distance = _distance_km(
        project.get("latitude"), project.get("longitude"), contractor.get("latitude"), contractor.get("longitude")
    )
    if math.isfinite(distance):
        if distance <= 25:
            return 14.0, ["Within 25 km of project"], [], [], 14.0
        if distance <= 100:
            return 8.0, ["Within 100 km of project"], [], [], 8.0

    return 0.0, [], [], ["Geography information unavailable"], 0.0


def _score_bid_timing(project: dict[str, Any]) -> tuple[float, list[str], list[str], list[str], float]:
    bid_date = project.get("bid_date")
    if bid_date is None:
        return 0.0, [], [], ["Bid date unavailable"], 0.0
    return 5.0, ["Project has bid date available"], [], [], 5.0


def _confidence_label(match_score: float, feature_completeness: float) -> str:
    if match_score >= 0.75 and feature_completeness >= 0.67:
        return "HIGH"
    if match_score >= 0.45 and feature_completeness >= 0.34:
        return "MEDIUM"
    return "LOW"


def rank_matches(project: dict[str, Any], contractors: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for contractor in contractors:
        trade_score, trade_positive, trade_negative, trade_unknown, trade_max = _score_trade_overlap(project, contractor)
        geo_score, geo_positive, geo_negative, geo_unknown, geo_max = _score_geography(project, contractor)
        timing_score, timing_positive, timing_negative, timing_unknown, timing_max = _score_bid_timing(project)

        known_components = []
        raw_score = 0.0
        max_available_score = 0.0

        if trade_max > 0:
            known_components.append("trade_overlap")
            raw_score += trade_score
            max_available_score += trade_max
        if geo_max > 0:
            known_components.append("geography")
            raw_score += geo_score
            max_available_score += geo_max
        if timing_max > 0:
            known_components.append("bid_timing")
            raw_score += timing_score
            max_available_score += timing_max

        match_score = round(raw_score / max_available_score, 4) if max_available_score else 0.0
        feature_completeness = round(len(known_components) / len(SUPPORTED_FEATURES), 4)
        confidence = _confidence_label(match_score, feature_completeness)

        positive_factors = trade_positive + geo_positive + timing_positive
        negative_factors = trade_negative + geo_negative + timing_negative
        unknown_factors = trade_unknown + geo_unknown + timing_unknown

        components = {
            "trade_overlap": {"score": round(trade_score, 2), "max": trade_max, "known": trade_max > 0},
            "geography": {"score": round(geo_score, 2), "max": geo_max, "known": geo_max > 0},
            "bid_timing": {"score": round(timing_score, 2), "max": timing_max, "known": timing_max > 0},
        }

        ranked.append(
            {
                "project_id": project.get("id") or project.get("source_id") or "unknown-project",
                "contractor_id": contractor.get("id") or contractor.get("source_id") or "unknown-contractor",
                "contractor_name": contractor.get("company_name") or contractor.get("normalized_name") or contractor.get("name") or "Unknown contractor",
                "raw_score": round(raw_score, 2),
                "max_available_score": round(max_available_score, 2),
                "match_score": match_score,
                "feature_completeness": feature_completeness,
                "confidence": confidence,
                "positive_factors": positive_factors,
                "negative_factors": negative_factors,
                "unknown_factors": unknown_factors,
                "components": components,
                "matcher_version": MATCHER_VERSION,
            }
        )

    ranked.sort(key=lambda item: (-item["match_score"], -item["raw_score"], item["contractor_name"]))
    for index, item in enumerate(ranked, start=1):
        item["ranking"] = index
    return ranked


def match_project(project: dict[str, Any], contractors: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return rank_matches(project, contractors)


__all__ = ["MATCHER_VERSION", "SUPPORTED_FEATURES", "normalize_trade_name", "rank_matches", "match_project"]
