import json
from typing import Dict, Any
from pathlib import Path


def _fixture_path(name: str) -> str:
    # Walk up until we find a docs/fixtures directory
    p = Path(__file__).resolve()
    for parent in p.parents:
        candidate = parent / "docs" / "fixtures" / name
        if candidate.exists():
            return str(candidate)
    # Fallback: relative to repository root (best-effort)
    return str(Path(__file__).resolve().parents[3] / "docs" / "fixtures" / name)


class MockBidProvider:
    def __init__(self):
        path = _fixture_path("synthetic_projects.json")
        with open(path, "r", encoding="utf8") as f:
            self.projects = json.load(f)

    def list_projects(self, filters: Dict[str, Any] = None, page_token: str = None) -> Dict[str, Any]:
        # Simple deterministic filter by state/trade
        results = self.projects
        if filters:
            state = filters.get("state")
            if state:
                results = [p for p in results if p.get("state") == state]
        return {"projects": results, "next_page_token": None}
